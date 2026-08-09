"""
数据修复脚本 v2

读取 dq_issues.csv，按问题类型分发到不同修复策略：
  - completeness_missing (字段缺失): 用 DOI 反查 Crossref/OpenAlex 补全
  - completeness_missing_but_pdf_available (摘要缺失但有 PDF):
      从 paper_fulltext 的 abstract 章节回补
  - validity_invalid_format (DOI/ISSN/ORCID/日期格式): 标准化
      - DOI: 转小写
      - ISSN: 多个用 ; 分隔时取第一个有效的
      - ORCID: 16 位数字 → XXXX-XXXX-XXXX-XXXX 格式
      - 日期: 尝试解析多种格式统一为 ISO (YYYY-MM-DD)
  - validity_case_inconsistent (DOI 大小写不统一): 转小写
  - consistency_negative (citation_count 负值): 截断为 0
  - consistency_mismatch (references_count 与 citations_v2 不一致):
      以 citations_v2 实际条数为准更新 references_count

用法：
    python data_fixer.py --issues dq_output/dq_issues.csv
    python data_fixer.py --issues dq_output/dq_issues.csv --dry-run
    python data_fixer.py --issues dq_output/dq_issues.csv --types validity,consistency
"""
import re
import json
import sys
import time
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

# 确保独立运行时能找到同级模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from db import get_connection
from logger import get_logger

LOGGER = get_logger("data_fixer")

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[^\s]+$")
ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
ISSN_PATTERN = re.compile(r"^\d{4}-\d{3}[\dX]$")
# ISO 日期：YYYY / YYYY-MM / YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

# Crossref polite pool
CROSSREF_BASE = "https://api.crossref.org/works"
MAILTO = config.CROSSREF_MAILTO or "research@example.com"
UA = {"User-Agent": f"literature-system/0.1 (mailto:{MAILTO})"}


# ============================================================
# 1. Crossref / OpenAlex 反查元数据（用于 completeness_missing）
# ============================================================
def fetch_crossref_by_doi(doi: str, timeout: int = 30) -> Optional[Dict]:
    """通过 DOI 反查 Crossref 元数据。"""
    try:
        url = f"{CROSSREF_BASE}/{doi}"
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("message", {})
        LOGGER.warning(f"  Crossref 查询 {doi} 失败: HTTP {r.status_code}")
    except Exception as e:
        LOGGER.warning(f"  Crossref 查询 {doi} 异常: {e}")
    return None


def extract_fields_from_crossref(msg: Dict) -> Dict:
    """从 Crossref message 提取可补全字段。"""
    fields = {}

    title = msg.get("title") or []
    if title:
        fields["title"] = title[0]

    abstract = msg.get("abstract")
    if abstract:
        # Crossref abstract 通常带 <jats:p> 标签，简单清理
        fields["abstract"] = re.sub(r"<[^>]+>", "", abstract).strip()

    container = msg.get("container-title") or []
    if container:
        fields["journal"] = container[0]

    pub_date = msg.get("published") or msg.get("published-print") or msg.get("published-online")
    if pub_date:
        parts = pub_date.get("date-parts", [[None]])
        if parts and parts[0]:
            y, m, d = (parts[0] + [None, None, None])[:3]
            if y:
                fields["published_date"] = "-".join(
                    str(x) for x in [y, m, d] if x is not None
                )

    issn_list = msg.get("ISSN") or []
    if issn_list:
        fields["issn"] = issn_list[0]

    vol = msg.get("volume")
    if vol:
        fields["volume"] = vol
    issue = msg.get("issue")
    if issue:
        fields["issue"] = issue
    page = msg.get("page")
    if page:
        fields["page"] = page

    # 作者（Crossref 格式：[{given, family, ORCID, affiliation, sequence}]）
    authors = msg.get("author") or []
    if authors:
        author_list = []
        for a in authors:
            entry = {
                "given": a.get("given", ""),
                "family": a.get("family", ""),
            }
            orcid = a.get("ORCID", "")
            if orcid:
                # 提取 16 位数字
                digits = re.sub(r"\D", "", orcid)
                if len(digits) == 16:
                    entry["ORCID"] = f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:]}"
            aff = a.get("affiliation") or []
            if aff:
                entry["affiliation"] = [x.get("name", "") for x in aff if x.get("name")]
            author_list.append(entry)
        fields["author"] = json.dumps(author_list, ensure_ascii=False)

    # references_count
    refs = msg.get("reference") or []
    if refs:
        fields["references_count"] = len(refs)

    return fields


def apply_crossref_backfill(conn, paper_id: int, doi: str, missing_fields: List[str]) -> Tuple[bool, List[str]]:
    """通过 DOI 反查 Crossref 并补全缺失字段。

    Returns:
        (是否更新, 实际更新字段列表)
    """
    if not doi:
        return False, []

    msg = fetch_crossref_by_doi(doi)
    if not msg:
        return False, []

    new_fields = extract_fields_from_crossref(msg)

    # 只补全报告里指出缺失的字段
    updates = {}
    for f in missing_fields:
        if f in new_fields and new_fields[f]:
            updates[f] = new_fields[f]

    if not updates:
        return False, []

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE papers SET {set_clause} WHERE id = ?",
        list(updates.values()) + [paper_id],
    )
    return True, list(updates.keys())


# ============================================================
# 2. 从 PDF 全文回补摘要
# ============================================================
def apply_abstract_backfill_from_pdf(conn, paper_id: int) -> Tuple[bool, str]:
    """从 paper_sections 的 abstract 章节提取摘要回补 papers.abstract。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT content FROM paper_sections WHERE paper_id = ? AND section_type = 'abstract' LIMIT 1",
        (paper_id,),
    )
    row = cur.fetchone()
    if not row or not row["content"] or len(row["content"]) < 50:
        return False, ""

    abstract = row["content"].strip()
    cur.execute("UPDATE papers SET abstract = ? WHERE id = ?", (abstract, paper_id))
    return True, abstract[:80]


# ============================================================
# 3. DOI 标准化（大小写）
# ============================================================
def normalize_doi(doi: str) -> str:
    """DOI 全小写化。"""
    return doi.lower() if doi else doi


def apply_doi_normalize(conn, paper_id: int, doi: str) -> bool:
    """更新 DOI 大小写。"""
    new_doi = normalize_doi(doi)
    if new_doi == doi:
        return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE papers SET doi = ? WHERE id = ?", (new_doi, paper_id))
        return True
    except sqlite3.IntegrityError:
        # 已经存在小写 DOI 了
        return False


# ============================================================
# 4. ORCID 标准化
# ============================================================
def normalize_orcid(orcid: str) -> Optional[str]:
    """将各种 ORCID 输入格式统一为 XXXX-XXXX-XXXX-XXXX。"""
    if not orcid:
        return None
    digits = re.sub(r"\D", "", orcid)
    if len(digits) == 16:
        return f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:]}"
    # 若已带 X 校验位
    if len(orcid) == 19 and ORCID_PATTERN.match(orcid):
        return orcid
    return None


def apply_orcid_normalize(conn, paper_id: int) -> Tuple[int, int]:
    """遍历 author JSON，标准化所有 ORCID 字段。

    Returns:
        (修复作者数, 检查作者数)
    """
    cur = conn.cursor()
    cur.execute("SELECT author FROM papers WHERE id = ?", (paper_id,))
    row = cur.fetchone()
    if not row or not row["author"]:
        return 0, 0

    try:
        authors = json.loads(row["author"]) if isinstance(row["author"], str) else row["author"]
    except (json.JSONDecodeError, TypeError):
        return 0, 0

    if not isinstance(authors, list):
        return 0, 0

    fixed = 0
    changed = False
    for a in authors:
        if isinstance(a, dict) and a.get("ORCID"):
            normalized = normalize_orcid(a["ORCID"])
            if normalized and normalized != a["ORCID"]:
                a["ORCID"] = normalized
                changed = True
                fixed += 1

    if changed:
        cur.execute(
            "UPDATE papers SET author = ? WHERE id = ?",
            (json.dumps(authors, ensure_ascii=False), paper_id),
        )
    return fixed, len(authors)


# ============================================================
# 5. 日期格式统一
# ============================================================
def normalize_date(date_str: str) -> Optional[str]:
    """尝试解析多种日期格式，统一为 ISO (YYYY-MM-DD)。"""
    if not date_str or DATE_PATTERN.match(date_str):
        return date_str  # 已经合法

    candidates = [
        "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
        "%d/%m/%Y", "%d-%m-%Y",
        "%B %d, %Y", "%b %d, %Y",
        "%Y %B %d", "%Y %b %d",
        "%Y",
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # 尝试从字符串里提取年份
    m = re.search(r"\b(19|20)\d{2}\b", date_str)
    if m:
        return m.group(0)

    return None


def apply_date_normalize(conn, paper_id: int, date_str: str) -> Tuple[bool, str]:
    new_date = normalize_date(date_str)
    if not new_date or new_date == date_str:
        return False, date_str
    cur = conn.cursor()
    cur.execute("UPDATE papers SET published_date = ? WHERE id = ?", (new_date, paper_id))
    return True, new_date


# ============================================================
# 6. citation_count 负值修正
# ============================================================
def apply_negative_citation_fix(conn, paper_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("UPDATE papers SET citation_count = 0 WHERE id = ? AND citation_count < 0", (paper_id,))
    return cur.rowcount > 0


# ============================================================
# 7. references_count 与 citations_v2 同步
# ============================================================
def apply_references_sync(conn, paper_id: int) -> Tuple[bool, int, int]:
    cur = conn.cursor()
    cur.execute("SELECT references_count FROM papers WHERE id = ?", (paper_id,))
    row = cur.fetchone()
    if not row:
        return False, 0, 0
    expected = row["references_count"]
    cur.execute("SELECT COUNT(*) AS c FROM citations_v2 WHERE citing_paper_id = ?", (paper_id,))
    actual = cur.fetchone()["c"]
    if expected != actual:
        cur.execute("UPDATE papers SET references_count = ? WHERE id = ?", (actual, paper_id))
        return True, expected, actual
    return False, expected, actual


# ============================================================
# 主入口：读取 dq_issues.csv 分发到不同修复策略
# ============================================================
def fix_data(issues_file: Path, dry_run: bool = False, types: Optional[List[str]] = None,
             limit: Optional[int] = None) -> Dict:
    """读取 dq_issues.csv，按 issue_type 分发到不同修复策略。"""
    if not issues_file.exists():
        LOGGER.error(f"问题文件不存在: {issues_file}")
        return {}

    import csv
    with issues_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        issues = list(reader)

    if limit:
        issues = issues[:limit]
    LOGGER.info(f"加载 {len(issues)} 条 DQ 问题")

    # 按 paper_id 分组
    by_paper: Dict[int, List[Dict]] = {}
    for issue in issues:
        pid = int(issue["paper_id"])
        by_paper.setdefault(pid, []).append(issue)

    # 类型过滤
    if types:
        types_set = set(types)
        by_paper = {
            pid: [i for i in iss if i["issue_type"] in types_set or
                  any(i["issue_type"].startswith(t) for t in types_set)]
            for pid, iss in by_paper.items()
        }
        by_paper = {k: v for k, v in by_paper.items() if v}
    LOGGER.info(f"涉及 {len(by_paper)} 篇论文需要修复")

    stats = {
        "papers_processed": 0,
        "crossref_backfill": 0,
        "abstract_backfill_pdf": 0,
        "doi_normalized": 0,
        "orcid_normalized": 0,
        "date_normalized": 0,
        "negative_citation_fixed": 0,
        "references_synced": 0,
        "errors": 0,
    }

    conn = get_connection(init_schema=False, row_factory=True)
    try:
        for pid, paper_issues in by_paper.items():
            stats["papers_processed"] += 1
            try:
                # 取 DOI
                cur = conn.cursor()
                cur.execute("SELECT doi FROM papers WHERE id = ?", (pid,))
                row = cur.fetchone()
                doi = row["doi"] if row else None

                for issue in paper_issues:
                    itype = issue["issue_type"]
                    field = issue["field"]

                    if itype == "completeness_missing":
                        if not doi:
                            continue
                        # 跨 API 礼貌延迟
                        time.sleep(1)
                        ok, fields = apply_crossref_backfill(conn, pid, doi, [field])
                        if ok:
                            stats["crossref_backfill"] += 1
                            LOGGER.info(f"  [paper {pid}] Crossref 补全: {fields}")

                    elif itype == "completeness_missing_but_pdf_available":
                        ok, snippet = apply_abstract_backfill_from_pdf(conn, pid)
                        if ok:
                            stats["abstract_backfill_pdf"] += 1
                            LOGGER.info(f"  [paper {pid}] 从 PDF 回补摘要: {snippet}...")

                    elif itype == "validity_case_inconsistent" and field == "doi":
                        if doi and apply_doi_normalize(conn, pid, doi):
                            stats["doi_normalized"] += 1
                            LOGGER.info(f"  [paper {pid}] DOI 大小写已标准化")

                    elif itype == "validity_invalid_format" and field == "author.orcid":
                        n_fixed, n_total = apply_orcid_normalize(conn, pid)
                        if n_fixed:
                            stats["orcid_normalized"] += n_fixed
                            LOGGER.info(f"  [paper {pid}] ORCID 标准化: {n_fixed}/{n_total}")

                    elif itype in ("validity_invalid_format", "consistency_invalid_format") and field == "published_date":
                        cur2 = conn.cursor()
                        cur2.execute("SELECT published_date FROM papers WHERE id = ?", (pid,))
                        r2 = cur2.fetchone()
                        if r2:
                            ok, new_date = apply_date_normalize(conn, pid, r2["published_date"])
                            if ok:
                                stats["date_normalized"] += 1
                                LOGGER.info(f"  [paper {pid}] 日期标准化: {r2['published_date']} → {new_date}")

                    elif itype == "consistency_negative" and field == "citation_count":
                        if apply_negative_citation_fix(conn, pid):
                            stats["negative_citation_fixed"] += 1
                            LOGGER.info(f"  [paper {pid}] citation_count 负值已截断为 0")

                    elif itype == "consistency_mismatch" and field == "references_count":
                        ok, exp, act = apply_references_sync(conn, pid)
                        if ok:
                            stats["references_synced"] += 1
                            LOGGER.info(f"  [paper {pid}] references_count 同步: {exp} → {act}")

                if not dry_run:
                    conn.commit()
            except Exception as e:
                stats["errors"] += 1
                LOGGER.error(f"  [paper {pid}] 修复异常: {e}")
                conn.rollback()

    finally:
        conn.close()

    LOGGER.info("=" * 60)
    LOGGER.info("数据修复统计")
    LOGGER.info("=" * 60)
    LOGGER.info(f"处理论文数: {stats['papers_processed']}")
    LOGGER.info(f"Crossref 字段补全: {stats['crossref_backfill']}")
    LOGGER.info(f"PDF 摘要回补: {stats['abstract_backfill_pdf']}")
    LOGGER.info(f"DOI 标准化: {stats['doi_normalized']}")
    LOGGER.info(f"ORCID 标准化: {stats['orcid_normalized']}")
    LOGGER.info(f"日期标准化: {stats['date_normalized']}")
    LOGGER.info(f"负引用修正: {stats['negative_citation_fixed']}")
    LOGGER.info(f"参考文献数同步: {stats['references_synced']}")
    LOGGER.info(f"错误数: {stats['errors']}")
    if dry_run:
        LOGGER.info("[dry-run 模式] 未提交实际更改")

    return stats


def parse_args():
    parser = argparse.ArgumentParser(description="DQ 数据修复 v2")
    parser.add_argument("--issues", default=str(config.ROOT_DIR / "db" / "dq_output" / "dq_issues.csv"), help="dq_issues.csv 路径")
    parser.add_argument("--dry-run", action="store_true", help="只输出修复计划不实际提交")
    parser.add_argument("--types", help="只处理某些 issue_type（逗号分隔，前缀匹配）")
    parser.add_argument("--limit", type=int, help="限制处理条数")
    return parser.parse_args()


def main():
    args = parse_args()
    types = args.types.split(",") if args.types else None
    fix_data(Path(args.issues), dry_run=args.dry_run, types=types, limit=args.limit)


if __name__ == "__main__":
    main()
