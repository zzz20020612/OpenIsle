"""
正文内引用标注提取与关联

支持主流引用格式：
  - APA/Harvard: (Author, Year) / (Author1 & Author2, Year) / (Author et al., Year)
  - IEEE/Vancouver: [1] / [1,2,3] / [1-3] / 1
  - Nature: 上标 1 或 [1]

输出：
  - 每条引用标注的位置（章节 + 字符偏移）
  - 与 citations_v2 表中参考文献的关联（按编号或 作者+年份 匹配）
"""
import re
import sqlite3
from typing import List, Dict, Optional, Tuple
from collections import Counter

from logger import get_logger
from pdf.scheduler import get_conn

log = get_logger("in_text_cite")

# ============================================================
# 引用标注正则
# ============================================================

# APA: (Author, Year) / (Author1 & Author2, Year) / (Author et al., Year)
# 注意要避免匹配 (Year) 单独的年份
APA_PATTERN = re.compile(
    r"\(("
    r"[A-Z][a-zA-Z]+(?:\s+(?:&|and)\s+[A-Z][a-zA-Z]+)?"
    r"(?:\s+et\s+al\.?)?"
    r",?\s+\d{4}[a-z]?"
    r"(?:,\s*[a-z]+)?"
    r")\)",
    re.M,
)

# IEEE/Vancouver: [1] / [1,2,3] / [1-3] / [1, 2-5]
IEEE_PATTERN = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")

# Nature: 单纯数字上标（少见，易误判，默认关闭）
NUMERIC_SUPERSCRIPT = re.compile(r"(?<!\w)(\d{1,3})(?![\d\w])")


def extract_apa_citations(text: str) -> List[Dict]:
    """提取 APA 格式引用标注。

    Returns: [{marker, authors, year, position_start, position_end}]
    """
    results = []
    for m in APA_PATTERN.finditer(text):
        inner = m.group(1)
        # 拆分作者和年份
        # 例如: "Gordon 2018" / "Briske et al. 2011" / "Foley et al. 2005, Schieltz and Rubenstein 2016"
        # 多个引用用 ; 或 , 分隔（但是作者内部也可能用 ,）
        # 简单处理：找所有 4 位年份
        years = re.findall(r"\b(1[89]\d{2}|20[0-5]\d)[a-z]?\b", inner)
        # 提取作者（年份之前的部分）
        # 按年份拆分
        for y in years:
            results.append({
                "marker": m.group(0),
                "year": y,
                "authors": "",  # 暂不解析作者
                "position_start": m.start(),
                "position_end": m.end(),
                "style": "apa",
            })
    return results


def extract_ieee_citations(text: str) -> List[Dict]:
    """提取 IEEE/Vancouver 格式引用标注 [N] / [N,M] / [N-M]。"""
    results = []
    for m in IEEE_PATTERN.finditer(text):
        inner = m.group(1)
        # 解析编号列表，如 "1,2,3" 或 "1-3" 或 "1, 2-5"
        nums = _parse_ieee_numbers(inner)
        for n in nums:
            results.append({
                "marker": m.group(0),
                "ref_number": n,
                "position_start": m.start(),
                "position_end": m.end(),
                "style": "ieee",
            })
    return results


def _parse_ieee_numbers(s: str) -> List[int]:
    """解析 IEEE 引用编号字符串。如 "1,2,3" → [1,2,3]，"1-3" → [1,2,3]。"""
    nums = []
    parts = re.split(r"\s*,\s*", s)
    for p in parts:
        if "-" in p:
            # 范围：1-3 → 1,2,3
            m = re.match(r"(\d+)\s*-\s*(\d+)", p)
            if m:
                start, end = int(m.group(1)), int(m.group(2))
                nums.extend(range(start, end + 1))
        else:
            try:
                nums.append(int(p))
            except ValueError:
                pass
    return nums


# ============================================================
# 主提取函数
# ============================================================
def extract_all_citations(text: str) -> List[Dict]:
    """提取所有格式的引用标注。"""
    apa = extract_apa_citations(text)
    ieee = extract_ieee_citations(text)

    # 合并去重（同一位置可能是 APA 又被误判为 IEEE）
    all_cites = apa + ieee
    all_cites.sort(key=lambda x: x["position_start"])
    return all_cites


def extract_citations_for_paper(paper_id: int) -> Dict:
    """提取一篇论文所有章节的引用标注，并尝试与 citations_v2 关联。

    Returns:
        {
            "total_citations": N,
            "by_section": [{section_id, section_type, heading, citation_count, citations: [...]}],
            "matched_to_refs": N,  # 成功关联到 citations_v2 的数量
            "unmatched": N,
        }
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 取所有非 references 章节
    cur.execute(
        """SELECT id, section_type, heading, content FROM paper_sections
           WHERE paper_id = ? AND section_type NOT IN ('references', 'acknowledgments')
           ORDER BY order_idx""",
        (paper_id,),
    )
    sections = cur.fetchall()

    # 2. 取已入库的参考文献（用于关联）
    cur.execute(
        """SELECT id, cited_doi, cited_title, cited_authors, cited_year,
                  raw_reference, match_method
           FROM citations_v2 WHERE citing_paper_id = ?
           ORDER BY id""",
        (paper_id,),
    )
    refs = cur.fetchall()
    refs_list = [dict(r) for r in refs]
    # 按编号映射（IEEE 引用 [N] 对应第 N 条参考文献）
    refs_by_number = {i + 1: r for i, r in enumerate(refs_list)}

    conn.close()

    # 3. 逐章节提取
    by_section = []
    total_cites = 0
    matched = 0
    unmatched = 0

    for sec in sections:
        sec = dict(sec)
        content = sec.get("content", "") or ""
        citations = extract_all_citations(content)

        # 尝试关联
        for c in citations:
            if c["style"] == "ieee":
                # 按 [N] 编号匹配
                ref_num = c.get("ref_number")
                if ref_num and ref_num in refs_by_number:
                    c["matched_ref_id"] = refs_by_number[ref_num]["id"]
                    c["matched_doi"] = refs_by_number[ref_num]["cited_doi"]
                    matched += 1
                else:
                    c["matched_ref_id"] = None
                    unmatched += 1
            else:
                # APA: 按 (作者, 年份) 模糊匹配
                year = c.get("year")
                if year:
                    # 在 refs 中找年份匹配的
                    candidates = [r for r in refs_list if r["cited_year"] == year]
                    if len(candidates) == 1:
                        c["matched_ref_id"] = candidates[0]["id"]
                        c["matched_doi"] = candidates[0]["cited_doi"]
                        matched += 1
                    elif len(candidates) > 1:
                        # 多个同年份，无法精确匹配，标 unmatched
                        c["matched_ref_id"] = None
                        unmatched += 1
                    else:
                        c["matched_ref_id"] = None
                        unmatched += 1
                else:
                    c["matched_ref_id"] = None
                    unmatched += 1

        total_cites += len(citations)
        by_section.append({
            "section_id": sec["id"],
            "section_type": sec["section_type"],
            "heading": sec["heading"],
            "citation_count": len(citations),
            "citations_sample": citations[:3],  # 仅取前 3 个样本
        })

    return {
        "total_citations": total_cites,
        "by_section": by_section,
        "matched_to_refs": matched,
        "unmatched": unmatched,
        "refs_count": len(refs_list),
    }


if __name__ == "__main__":
    # 自测：直接解析一段文本
    sample = """Livestock farming significantly influences vegetation structure (Gordon 2018).
    Additionally, livestock presence disrupts wildlife behaviour (Briske et al. 2011).
    Some studies [1,2,3] show different results. Another approach [4-6] confirms this.
    As noted by Foley et al. (2005), the conversion of land for grazing reduces availability.
    """
    print("=== 测试引用标注提取 ===")
    cites = extract_all_citations(sample)
    print(f"提取到 {len(cites)} 条引用:")
    for c in cites:
        if c["style"] == "apa":
            print(f"  APA: {c['marker']} (year={c['year']}) pos={c['position_start']}")
        else:
            print(f"  IEEE: {c['marker']} (ref_num={c.get('ref_number')}) pos={c['position_start']}")
