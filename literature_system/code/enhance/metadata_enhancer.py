"""
PDF 元数据增强模块（TODO 2.2）

功能：
  1. 摘要回写：从 paper_sections 表中读取 abstract 章节，回写到 papers.abstract
     规则：仅当 papers.abstract IS NULL OR length < 50 时覆盖，避免破坏元数据
  2. 作者/机构比对：从 PDF 提取作者行，与 papers.author JSON 字段比对
     规则：只标记差异，不自动覆盖
  3. 基金关联：从 acknowledgments 章节提取 grant number，与 funders 表模糊匹配
     规则：置信度低的入库到 paper_funders 表并标记 match_confidence
"""
import re
import json
import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from logger import get_logger
from pdf.scheduler import get_conn

log = get_logger("metadata_enhancer")


# ============================================================
# 1. 摘要回写
# ============================================================
def backfill_abstract(paper_id: int, min_length: int = 50) -> Dict:
    """从 paper_sections 中读取 abstract 章节，回写到 papers.abstract。

    Args:
        paper_id: 论文 ID
        min_length: 当 papers.abstract 长度小于此值时才回写

    Returns:
        {"paper_id": N, "action": "backfilled|skipped|no_abstract_section",
         "old_length": N, "new_length": N}
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 读取当前 abstract
    cur.execute("SELECT abstract FROM papers WHERE id = ?", (paper_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"paper_id": paper_id, "action": "paper_not_found"}
    current_abstract = row["abstract"] or ""
    current_len = len(current_abstract)

    # 2. 已有充足摘要则跳过
    if current_len >= min_length:
        conn.close()
        return {
            "paper_id": paper_id,
            "action": "skipped",
            "old_length": current_len,
            "new_length": current_len,
        }

    # 3. 从 paper_sections 读 abstract 章节
    cur.execute(
        """SELECT content FROM paper_sections
           WHERE paper_id = ? AND section_type = 'abstract'
           ORDER BY order_idx LIMIT 1""",
        (paper_id,),
    )
    sec_row = cur.fetchone()
    if not sec_row or not sec_row["content"]:
        conn.close()
        return {"paper_id": paper_id, "action": "no_abstract_section"}

    new_abstract = sec_row["content"].strip()
    if len(new_abstract) < 50:
        conn.close()
        return {
            "paper_id": paper_id,
            "action": "skipped",
            "old_length": current_len,
            "new_length": current_len,
            "reason": "pdf_abstract_too_short",
        }

    # 4. 回写
    cur.execute(
        "UPDATE papers SET abstract = ? WHERE id = ?",
        (new_abstract, paper_id),
    )
    conn.commit()
    conn.close()

    log.info(f"[abstract] paper_id={paper_id} 回写摘要: "
             f"{current_len} → {len(new_abstract)} 字符")
    return {
        "paper_id": paper_id,
        "action": "backfilled",
        "old_length": current_len,
        "new_length": len(new_abstract),
    }


def backfill_abstract_batch(paper_ids: Optional[List[int]] = None) -> Dict:
    """批量摘要回写。

    Args:
        paper_ids: 指定论文 ID 列表；None 则处理所有

    Returns:
        {"total": N, "backfilled": N, "skipped": N, "no_section": N}
    """
    conn = get_conn()
    cur = conn.cursor()
    if paper_ids is None:
        # 找出所有已有 paper_sections 的论文
        cur.execute("SELECT DISTINCT paper_id FROM paper_sections")
        paper_ids = [r[0] for r in cur.fetchall()]
    conn.close()

    stats = {"total": len(paper_ids), "backfilled": 0, "skipped": 0, "no_section": 0, "not_found": 0}
    for pid in paper_ids:
        result = backfill_abstract(pid)
        action = result["action"]
        if action == "backfilled":
            stats["backfilled"] += 1
        elif action == "skipped":
            stats["skipped"] += 1
        elif action == "no_abstract_section":
            stats["no_section"] += 1
        else:
            stats["not_found"] += 1

    log.info(f"[abstract] 批量回写: {stats}")
    return stats


# ============================================================
# 2. 作者/机构比对
# ============================================================
# PDF 首页作者行提取正则
# 常见格式: "Author One1, Author Two2,3,* & Author Three4"
#          "Author One1*, Author Two2, Author Three3,4"
AUTHOR_LINE_PATTERN = re.compile(
    r"^([A-Z][a-zA-Z\-\s,0-9\*&]+(?:\d+(?:[-,]\d+)*)?\s*[,;]\s*)+[A-Z][a-zA-Z\-\s,0-9\*&]+\d*(?:[-,]\d+)*\*?$",
    re.M,
)

# 机构提取（含数字上标引用）
AFFILIATION_PATTERN = re.compile(
    r"^(\d+\s+[A-Z][\w\s\-,.;]+(?:Department|University|Institute|Lab|Center|College|Ministry|School|Hospital|Research)[\w\s\-,.;.]*)$",
    re.M | re.I,
)


def extract_authors_affiliations_from_pdf(paper_id: int) -> Dict:
    """从 PDF 提取作者行和机构信息（基于 paper_fulltext 的前 2 页）。

    Returns:
        {"paper_id": N, "pdf_authors": [...], "pdf_affiliations": [...],
         "db_authors": [...], "differences": [...]}
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 取 PDF 前 2 页文本（论文头部）
    cur.execute(
        """SELECT full_text FROM paper_fulltext WHERE paper_id = ?""",
        (paper_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"paper_id": paper_id, "action": "no_fulltext"}
    full_text = row["full_text"] or ""

    # 取前 3000 字符（约 2 页）作为头部
    head_text = full_text[:3000]

    # 2. 从 papers.author JSON 字段读已有作者
    cur.execute("SELECT author FROM papers WHERE id = ?", (paper_id,))
    paper_row = cur.fetchone()
    db_authors = []
    if paper_row and paper_row["author"]:
        try:
            db_authors = json.loads(paper_row["author"]) if isinstance(paper_row["author"], str) else paper_row["author"]
        except json.JSONDecodeError:
            db_authors = []
    conn.close()

    # 3. 提取 PDF 作者行
    pdf_authors = _extract_author_names(head_text)
    pdf_affiliations = _extract_affiliations(head_text)

    # 4. 比对差异
    differences = _compare_authors(db_authors, pdf_authors)

    log.info(f"[authors] paper_id={paper_id}: PDF 提取 {len(pdf_authors)} 作者, "
             f"{len(pdf_affiliations)} 机构, {len(differences)} 处差异")

    return {
        "paper_id": paper_id,
        "pdf_authors": pdf_authors,
        "pdf_affiliations": pdf_affiliations,
        "db_authors": db_authors,
        "differences": differences,
    }


def _extract_author_names(head_text: str) -> List[str]:
    """从论文头部文本提取作者名。

    策略：
      - 找标题后的第一行（通常是作者行）
      - 按逗号/分号/&)
    """
    lines = head_text.split("\n")
    # 找标题行（通常较短、首字母大写、不含数字）
    title_idx = -1
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        if not line or len(line) < 10 or len(line) > 300:
            continue
        # 标题通常首字母大写且不含数字
        if line[0].isupper() and not any(c.isdigit() for c in line[:30]):
            title_idx = i
            break

    # 作者行在标题之后
    author_lines = []
    start = title_idx + 1 if title_idx >= 0 else 1
    for line in lines[start:start + 5]:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        # 作者行特征：含数字上标、&、逗号分隔
        if (AUTHOR_LINE_PATTERN.match(line) or
            ("&" in line and any(c.isdigit() for c in line)) or
            ("," in line and len(line.split(",")) >= 2)):
            author_lines.append(line)
            break

    if not author_lines:
        return []

    # 解析作者名
    author_str = author_lines[0]
    # 去掉数字上标
    author_str = re.sub(r"\d+(?:[-,]\d+)*", "", author_str)
    author_str = author_str.replace("*", "").strip(" ,;&")
    # 按 , ; & 拆分
    parts = re.split(r"\s*[,;]\s*|\s*&\s*", author_str)
    # 过滤空和过短
    authors = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]
    return authors


def _extract_affiliations(head_text: str) -> List[str]:
    """提取机构信息。"""
    affs = []
    for m in AFFILIATION_PATTERN.finditer(head_text):
        aff = m.group(1).strip()
        # 清理数字前缀
        aff = re.sub(r"^\d+\s+", "", aff)
        if aff and len(aff) > 10:
            affs.append(aff)
    return affs


def _compare_authors(db_authors: List, pdf_authors: List[str]) -> List[Dict]:
    """比对元数据作者与 PDF 提取作者，返回差异列表。"""
    differences = []

    # 标准化 db_authors（可能是 dict 列表或字符串列表）
    db_names = []
    for a in db_authors:
        if isinstance(a, dict):
            name = a.get("family", "") or a.get("name", "")
            given = a.get("given", "")
            full = f"{given} {name}".strip() if given else name
            if full:
                db_names.append(full)
        elif isinstance(a, str):
            db_names.append(a)

    db_set = set(n.lower() for n in db_names)
    pdf_set = set(n.lower() for n in pdf_authors)

    # PDF 有但 db 没有
    only_pdf = pdf_set - db_set
    for n in pdf_authors:
        if n.lower() in only_pdf:
            differences.append({
                "type": "pdf_only",
                "name": n,
                "detail": "PDF 提取到但元数据无",
            })

    # db 有但 PDF 没有
    only_db = db_set - pdf_set
    for n in db_names:
        if n.lower() in only_db:
            differences.append({
                "type": "db_only",
                "name": n,
                "detail": "元数据有但 PDF 未提取到",
            })

    return differences


# ============================================================
# 3. 基金/致谢关联
# ============================================================
# 基金号提取正则
GRANT_PATTERNS = [
    # EU Horizon: H2020, Horizon Europe
    re.compile(r"\b(H2020[-\s]?\d+|Horizon\s+\d+[-\s]?\d+|GA\s+\d+)\b", re.I),
    # NSF
    re.compile(r"\b(NSF[-\s]?\d+|DEB[-\s]?\d+|IOS[-\s]?\d+)\b", re.I),
    # NIH
    re.compile(r"\b(NIH[-\s]?\w*\d+|R01[A-Z0-9]+)\b", re.I),
    # ERC
    re.compile(r"\b(ERC[-\s]?\w+\d+)\b", re.I),
    # 通用 grant number: "grant no. XXX" / "funded by XXX" / "project XXX"
    re.compile(r"(?:grant|project|funded\s+by|contract)\s*(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9\-/]{4,30})", re.I),
    # DOI 形式基金
    re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]*fund[^\s\"<>]*)\b", re.I),
]


def extract_funders_from_pdf(paper_id: int) -> Dict:
    """从 acknowledgments 章节提取基金信息，关联到 funders 表。

    Returns:
        {"paper_id": N, "grant_numbers": [...], "matched_funders": [...],
         "unmatched": [...]}
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 读 acknowledgments 章节
    cur.execute(
        """SELECT content FROM paper_sections
           WHERE paper_id = ? AND section_type = 'acknowledgments'
           ORDER BY order_idx LIMIT 1""",
        (paper_id,),
    )
    row = cur.fetchone()
    if not row or not row["content"]:
        conn.close()
        return {"paper_id": paper_id, "action": "no_acknowledgments"}
    ack_text = row["content"]

    # 2. 提取基金号
    grant_numbers = []
    for pattern in GRANT_PATTERNS:
        for m in pattern.finditer(ack_text):
            grant = m.group(1) if m.groups() else m.group(0)
            grant = grant.strip().rstrip(".,;")
            if grant and grant not in grant_numbers:
                grant_numbers.append(grant)

    # 3. 取已有 funders 表
    cur.execute("SELECT id, name, doi, award FROM funders")
    all_funders = [dict(r) for r in cur.fetchall()]

    matched_funders = []
    unmatched = []

    for grant in grant_numbers:
        # 在 funders.award JSON 字段中找
        matched = False
        for f in all_funders:
            award_str = f.get("award", "")
            if award_str:
                try:
                    awards = json.loads(award_str) if isinstance(award_str, str) else award_str
                    if isinstance(awards, list) and grant in awards:
                        matched_funders.append({
                            "grant_number": grant,
                            "funder_id": f["id"],
                            "funder_name": f["name"],
                            "match_method": "award_exact",
                            "match_confidence": "high",
                        })
                        matched = True
                        break
                except json.JSONDecodeError:
                    pass
            # 名称模糊匹配（grant 含 funder.name）
            if f.get("name") and f["name"].lower() in grant.lower():
                matched_funders.append({
                    "grant_number": grant,
                    "funder_id": f["id"],
                    "funder_name": f["name"],
                    "match_method": "name_contains",
                    "match_confidence": "medium",
                })
                matched = True
                break
        if not matched:
            unmatched.append(grant)

    # 4. 高置信度匹配写入 paper_funders
    for m in matched_funders:
        if m["match_confidence"] == "high":
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO paper_funders (paper_id, funder_id) VALUES (?, ?)",
                    (paper_id, m["funder_id"]),
                )
            except sqlite3.Error as e:
                log.warning(f"[funders] paper_id={paper_id} 关联失败: {e}")
    conn.commit()
    conn.close()

    log.info(f"[funders] paper_id={paper_id}: 提取 {len(grant_numbers)} 个基金号, "
             f"匹配 {len(matched_funders)} 个 funder, 未匹配 {len(unmatched)} 个")

    return {
        "paper_id": paper_id,
        "grant_numbers": grant_numbers,
        "matched_funders": matched_funders,
        "unmatched": unmatched,
    }


# ============================================================
# 主入口
# ============================================================
def enhance_metadata(paper_id: int) -> Dict:
    """对一篇论文执行全部元数据增强。

    Returns:
        {"abstract": {...}, "authors": {...}, "funders": {...}}
    """
    return {
        "abstract": backfill_abstract(paper_id),
        "authors": extract_authors_affiliations_from_pdf(paper_id),
        "funders": extract_funders_from_pdf(paper_id),
    }


if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))

    # 自测：从已有的 MinerU 输出测试
    from pdf.pipeline import MineruAPIClient
    from pdf.ref_parser import save_references, parse_pdf_references

    PDF = Path(__file__).parent.parent / "pdfs" / "10.3897_arphapreprints.e142608.pdf"
    MINERU_OUT = Path(__file__).parent / "test" / "marker_gpu_test" / "mineru_doi_output"

    # 准备测试数据：先写 paper_fulltext + paper_sections
    class FakeMineruClient(MineruAPIClient):
        def __init__(self):
            pass
    result = FakeMineruClient()._convert_result(MINERU_OUT, PDF)

    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 清理旧测试数据
    cur.execute("DELETE FROM papers WHERE id = 999")
    cur.execute("DELETE FROM paper_fulltext WHERE paper_id = 999")
    cur.execute("DELETE FROM paper_sections WHERE paper_id = 999")
    cur.execute("DELETE FROM paper_funders WHERE paper_id = 999")

    # 插入 paper（模拟缺失 abstract）
    cur.execute(
        """INSERT INTO papers (id, doi, title, abstract, author)
           VALUES (?, ?, ?, NULL, ?)""",
        (999, "10.3897/arphapreprints.e142608", "Test paper",
         json.dumps([{"family": "Visconti", "given": "P."}])),
    )

    # 插入 fulltext
    cur.execute(
        """INSERT INTO paper_fulltext (paper_id, parser_used, parse_quality, full_text, char_count, page_count)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (999, "mineru", "high", result.full_text, result.char_count, result.page_count),
    )

    # 插入 sections
    for sec in result.sections:
        cur.execute(
            """INSERT INTO paper_sections (paper_id, section_type, heading, content, page_start, page_end, order_idx)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (999, sec["section_type"], sec["heading"], sec.get("content", ""),
             sec.get("page_start"), sec.get("page_end"), sec["order_idx"]),
        )
    conn.commit()
    conn.close()

    print(">>> 测试元数据增强...")
    stats = enhance_metadata(999)
    print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))

    # 验证
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT abstract FROM papers WHERE id = 999")
    r = cur.fetchone()
    print(f"\n回写后 abstract 长度: {len(r['abstract'] or '')}")
    print(f"abstract 前 200 字符: {(r['abstract'] or '')[:200]}")

    # 清理
    cur.execute("DELETE FROM papers WHERE id = 999")
    cur.execute("DELETE FROM paper_fulltext WHERE paper_id = 999")
    cur.execute("DELETE FROM paper_sections WHERE paper_id = 999")
    cur.execute("DELETE FROM paper_funders WHERE paper_id = 999")
    conn.commit()
    conn.close()
    print("\n已清理测试数据")
