"""
参考文献解析模块

双源融合：
  源 A：Crossref API references 字段（结构化、~40% 覆盖率、高置信度）
  源 B：PDF References 章节（正则解析自由文本、~100% 覆盖率、中低置信度）

匹配优先级：
  1. crossref_direct: Crossref 已结构化的引用
  2. doi_lookup:     PDF 中识别到 DOI → Crossref 反查
  3. regex:          PDF 正则匹配 (作者, 年份, 标题, 期刊)
  4. unmatched:      无法结构化，保留 raw_text

写入 citations_v2 表。
"""
import re
import time
import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import requests

import config
from logger import get_logger
from pdf.scheduler import get_conn

log = get_logger("ref_parser")

# ============================================================
# DOI 提取正则
# ============================================================
# DOI 标准格式：10.NNNN/xxxx
DOI_PATTERN = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
# 有些参考文献用 doi: 前缀
DOI_PREFIX_PATTERN = re.compile(r"doi:\s*(10\.\d{4,9}/[^\s\"<>]+)", re.I)

# 参考文献行：常见格式
# APA:    Author, A. A., & Author, B. B. (Year). Title. Journal, vol(issue), pages.
# IEEE:   [N] A. Author, "Title," Journal, vol. X, no. Y, pp. Z-Z, Year.
# Vancouver: Author AA, Author BB. Title. Journal. Year;Vol(Issue):Pages.
# 仅提取作者、年份、标题、期刊的近似模式
YEAR_PATTERN = re.compile(r"\b(1[89]\d{2}|20[0-5]\d)\b")
# 标题：通常在年份之后的句号后，到下一个句号
TITLE_PATTERN_APA = re.compile(
    r"\((\d{4})\)\.\s*([^.]+)\.\s*", re.I
)


def extract_doi_from_text(text: str) -> Optional[str]:
    """从文本中提取 DOI。"""
    m = DOI_PREFIX_PATTERN.search(text) or DOI_PATTERN.search(text)
    if m:
        doi = m.group(1).rstrip(".,;)")
        return doi.lower()
    return None


# ============================================================
# 源 A：Crossref references 字段
# ============================================================
def fetch_crossref_references(doi: str) -> List[Dict]:
    """从 Crossref API 获取论文的 references 字段。

    Returns:
        list of {cited_doi, cited_title, cited_authors, cited_year, cited_journal,
                 raw_reference, match_method="crossref_direct", match_confidence="high"}
    """
    if not doi:
        return []
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": config.CROSSREF_USER_AGENT}
    params = {}
    if config.CROSSREF_MAILTO:
        params["mailto"] = config.CROSSREF_MAILTO
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            log.info(f"[crossref] {doi}: status {r.status_code}, 无 references")
            return []
        data = r.json().get("message", {})
        refs = data.get("reference", [])
        if not refs:
            log.info(f"[crossref] {doi}: 无 reference 字段")
            return []
        result = []
        for ref in refs:
            cited_doi = ref.get("DOI", "").lower() or None
            cited_title = ref.get("article-title") or ref.get("unstructured") or ""
            cited_year = ref.get("year") or ""
            cited_journal = ref.get("journal-title") or ""
            authors_str = ""
            authors = ref.get("author", [])
            if authors:
                # Crossref refs 中 author 可能是 [{family, given}]（标准）或 ["Smith J"]（字符串）
                names = []
                for a in authors:
                    if isinstance(a, dict):
                        family = a.get("family", "")
                        given = a.get("given", "")
                        if family:
                            names.append(f"{family}, {given}" if given else family)
                    elif isinstance(a, str):
                        # 字符串作者：原样保留，过滤空值
                        if a.strip():
                            names.append(a.strip())
                authors_str = "; ".join(names)
            # raw_reference：拼接近似格式
            raw_parts = []
            if authors_str:
                raw_parts.append(authors_str)
            if cited_year:
                raw_parts.append(f"({cited_year})")
            if cited_title:
                raw_parts.append(cited_title)
            if cited_journal:
                raw_parts.append(cited_journal)
            raw_reference = ". ".join(raw_parts) if raw_parts else cited_title

            result.append({
                "cited_doi": cited_doi,
                "cited_title": cited_title,
                "cited_authors": authors_str,
                "cited_year": cited_year,
                "cited_journal": cited_journal,
                "raw_reference": raw_reference,
                "match_method": "crossref_direct",
                "match_confidence": "high",
            })
        log.info(f"[crossref] {doi}: 获取 {len(result)} 条 references")
        return result
    except requests.RequestException as e:
        log.warning(f"[crossref] {doi} 异常: {e}")
        return []


# ============================================================
# 源 B：PDF References 章节解析
# ============================================================
def parse_pdf_references(ref_text: str) -> List[Dict]:
    """解析 PDF References 章节的纯文本。

    策略：按行扫描，识别"新条目开头"作为分隔符。
    """
    if not ref_text:
        return []
    # 按行拆分，过滤空行
    lines = [line.strip() for line in ref_text.split("\n") if line.strip()]

    # 把跨行拆分的同一条引用合并
    # 新条目判定：以作者名/年份/编号开头
    grouped = []
    for line in lines:
        if not line:
            continue
        if grouped and _is_continuation_line(line, grouped[-1]):
            grouped[-1] = grouped[-1] + " " + line
        else:
            grouped.append(line)

    result = []
    for ref_line in grouped:
        if len(ref_line) < 20:
            continue
        # 提取 DOI（仅在该条引用范围内查找，避免跨条目匹配）
        doi = extract_doi_from_text(ref_line)
        year_match = YEAR_PATTERN.search(ref_line)
        year = year_match.group(1) if year_match else ""
        # 标题：取年份后到下一个句号之间的内容
        title = ""
        if year:
            tm = TITLE_PATTERN_APA.search(ref_line)
            if tm:
                title = tm.group(2).strip()
        result.append({
            "cited_doi": doi,
            "cited_title": title,
            "cited_authors": "",
            "cited_year": year,
            "cited_journal": "",
            "raw_reference": ref_line,
            "match_method": "doi_lookup" if doi else "regex" if (year or title) else "unmatched",
            "match_confidence": "high" if doi else "medium" if (year or title) else "low",
        })
    log.info(f"[pdf_refs] 解析 {len(result)} 条参考文献")
    return result


def _is_continuation_line(line: str, prev_line: str) -> bool:
    """判断当前行是否是上一行的延续（而非新条目开头）。

    新条目特征：
      - 以编号开头：1. / [1] / 1)
      - 以作者名开头：姓 + 首字母（如 "Smith J" / "Smith, J."）
      - 以年份开头：(2023)
    延续行特征：
      - 以小写字母开头
      - 以连字符开头
      - 以 URL 片段开头（http/https/www）
      - 上一行末尾是连字符或冒号
    """
    # URL 片段
    if re.match(r"^(https?://|www\.|/)", line, re.I):
        return True
    # 以小写开头
    if line[0].islower():
        return True
    # 连字符开头
    if line.startswith("-") or line.startswith("—"):
        return True
    # 上一行末尾是连字符或冒号或 URL
    if prev_line.endswith("-") or prev_line.endswith(":"):
        return True
    # 如果当前行明显是新条目（作者名/编号），则不是延续
    if _looks_like_new_ref(line):
        return False
    # 默认视为延续（参考文献正文常常以各种字符开头）
    return True


def _looks_like_new_ref(line: str) -> bool:
    """判断行是否像新的参考文献条目开头。

    新条目特征（按参考文献主流格式）：
      - APA:      "Author, A. A., & Author, B. B. (Year). Title..."
      - IEEE:     "[N] A. Author, "Title," ..."
      - Vancouver: "Author AA, Author BB. Title. Journal. Year;..."
      - 编号开头：  "1." "1)" "[1]" "1,"
    """
    # 编号开头：1. / 1) / [1] / 1,
    if re.match(r"^\[?\d+[\].,)]\s", line):
        return True
    # APA/Vancouver 作者名开头：姓 + 首字母（如 "Smith J A" / "Smith, J. A." / "Smith JA,")
    # 至少 2 个连续大写单词或 姓+首字母缩写
    if re.match(r"^[A-Z][a-z]+(\s+[A-Z]\b|,\s+[A-Z]\.|\s+[A-Z]{1,3}[,\s])", line):
        return True
    # 多个作者并列（如 "Smith J, Doe J" / "Smith, J., Doe, J."）
    if re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+,", line):
        return True
    # 年份开头（少见）
    if re.match(r"^\(\d{4}\)", line):
        return True
    return False


# ============================================================
# 双源融合
# ============================================================
def merge_references(
    crossref_refs: List[Dict], pdf_refs: List[Dict]
) -> List[Dict]:
    """融合 Crossref 与 PDF 双源参考文献。

    规则：
      - Crossref 优先（match_method=crossref_direct）
      - PDF 中提取到 DOI 的，如果 DOI 不在 Crossref 中，则用 doi_lookup
      - PDF 中无法结构化的，保留 raw_reference，标 unmatched
      - 按 raw_reference 去重（PDF 优先用原文，Crossref 用拼接）
    """
    seen_dois = set()
    merged = []

    # 1. 先放 Crossref（高置信度）
    for ref in crossref_refs:
        merged.append(ref)
        if ref.get("cited_doi"):
            seen_dois.add(ref["cited_doi"])

    # 2. 补充 PDF 独有的
    for ref in pdf_refs:
        doi = ref.get("cited_doi")
        if doi and doi in seen_dois:
            continue
        merged.append(ref)
        if doi:
            seen_dois.add(doi)

    log.info(f"[merge] Crossref {len(crossref_refs)} + PDF {len(pdf_refs)} → "
             f"融合后 {len(merged)} 条（去重 {len(crossref_refs) + len(pdf_refs) - len(merged)} 条）")
    return merged


# ============================================================
# DOI 反查 Crossref（可选增强）
# ============================================================
def lookup_doi_metadata(doi: str) -> Optional[Dict]:
    """用 DOI 反查 Crossref 获取元数据。"""
    if not doi:
        return None
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": config.CROSSREF_USER_AGENT}
    params = {}
    if config.CROSSREF_MAILTO:
        params["mailto"] = config.CROSSREF_MAILTO
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            return None
        msg = r.json().get("message", {})
        # 标题
        titles = msg.get("title", [])
        title = titles[0] if titles else ""
        # 年份
        year = ""
        issued = msg.get("issued", {}).get("date-parts", [[]])
        if issued and issued[0]:
            year = str(issued[0][0])
        # 作者
        authors = msg.get("author", [])
        names = []
        for a in authors:
            family = a.get("family", "")
            given = a.get("given", "")
            if family:
                names.append(f"{family}, {given}" if given else family)
        authors_str = "; ".join(names)
        # 期刊
        journal = msg.get("container-title", [])
        journal_name = journal[0] if journal else ""

        return {
            "cited_doi": doi,
            "cited_title": title,
            "cited_authors": authors_str,
            "cited_year": year,
            "cited_journal": journal_name,
        }
    except requests.RequestException:
        return None


# ============================================================
# 入库
# ============================================================
def save_references(paper_id: int, refs: List[Dict]) -> int:
    """把参考文献写入 citations_v2 表，返回入库条数。"""
    if not refs:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    try:
        for ref in refs:
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO citations_v2
                       (citing_paper_id, cited_doi, cited_title, cited_authors,
                        cited_year, cited_journal, raw_reference,
                        match_method, match_confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        paper_id,
                        ref.get("cited_doi"),
                        ref.get("cited_title", ""),
                        ref.get("cited_authors", ""),
                        ref.get("cited_year", ""),
                        ref.get("cited_journal", ""),
                        ref.get("raw_reference", ""),
                        ref.get("match_method", "unmatched"),
                        ref.get("match_confidence", "low"),
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            except sqlite3.Error as e:
                log.warning(f"入库失败: {e}, ref={ref.get('raw_reference', '')[:80]}")
        conn.commit()
        log.info(f"[db] citations_v2 paper_id={paper_id}: 写入 {inserted}/{len(refs)} 条")
    finally:
        conn.close()
    return inserted


# ============================================================
# 主入口
# ============================================================
def extract_and_save_references(
    paper_id: int,
    doi: Optional[str],
    references_section_text: str,
    doi_lookup_limit: int = 20,
) -> Dict[str, int]:
    """提取并保存一篇论文的参考文献。

    Args:
        paper_id: 论文 ID
        doi: 论文 DOI（用于 Crossref references 查询）
        references_section_text: PDF References 章节的纯文本
        doi_lookup_limit: 对 PDF 中提取到的 DOI 反查 Crossref 的数量上限

    Returns:
        {"crossref": N, "pdf": N, "merged": N, "inserted": N}
    """
    log.info(f"[ref] 开始处理 paper_id={paper_id} doi={doi}")

    # 源 A：Crossref
    crossref_refs = fetch_crossref_references(doi) if doi else []

    # 源 B：PDF References 章节
    pdf_refs = parse_pdf_references(references_section_text)

    # 融合
    merged = merge_references(crossref_refs, pdf_refs)

    # 增强：对 PDF 中提取到 DOI 但缺元数据的，反查 Crossref
    if doi_lookup_limit > 0:
        enhanced = 0
        for ref in merged:
            if enhanced >= doi_lookup_limit:
                break
            doi_ref = ref.get("cited_doi")
            if doi_ref and not ref.get("cited_title") and ref.get("match_method") == "doi_lookup":
                meta = lookup_doi_metadata(doi_ref)
                if meta:
                    ref.update({
                        "cited_title": meta["cited_title"],
                        "cited_authors": meta["cited_authors"],
                        "cited_year": meta["cited_year"],
                        "cited_journal": meta["cited_journal"],
                    })
                    ref["match_confidence"] = "high"
                    enhanced += 1
                    time.sleep(0.5)  # 礼貌限流
        if enhanced:
            log.info(f"[ref] DOI 反查增强 {enhanced} 条")

    # 入库
    inserted = save_references(paper_id, merged)

    return {
        "crossref": len(crossref_refs),
        "pdf": len(pdf_refs),
        "merged": len(merged),
        "inserted": inserted,
    }


if __name__ == "__main__":
    # 自测：用已有的 References 章节文本
    import sys
    import json

    # 从已有的 paper_sections 表中读取 References 章节
    if len(sys.argv) > 1:
        paper_id = int(sys.argv[1])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT content FROM paper_sections WHERE paper_id=? AND section_type='references'",
            (paper_id,),
        )
        row = cur.fetchone()
        cur.execute("SELECT doi FROM papers WHERE id=?", (paper_id,))
        doi_row = cur.fetchone()
        conn.close()
        if row and doi_row:
            stats = extract_and_save_references(
                paper_id=paper_id,
                doi=doi_row["doi"],
                references_section_text=row["content"],
            )
            print(json.dumps(stats, indent=2))
        else:
            print(f"paper_id={paper_id} 无 References 章节或 DOI")
    else:
        print("用法: python ref_parser.py <paper_id>")
