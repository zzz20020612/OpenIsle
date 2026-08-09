"""
引用网络分析与导出模块（TODO 2.3）

功能：
  1. DOI 归一化、去重与缺失 DOI 引用的模糊匹配
  2. 引用网络基础统计（入度 / 出度 / 连通性 / 被引核心论文）
  3. 引用网络导出（GEXF / CSV）
  4. 段落级引用追溯（引用标注 → 参考文献条目 → 被引论文 DOI）
"""
import re
import json
import sqlite3
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter, defaultdict
from pathlib import Path

from logger import get_logger
from pdf.scheduler import get_conn
from pdf.in_text_citations import extract_all_citations

log = get_logger("citation_network")


# ============================================================
# 1. DOI 归一化
# ============================================================
def normalize_doi(doi: str) -> Optional[str]:
    """DOI 归一化：去掉 URL 前缀、统一小写、去尾部标点。"""
    if not doi:
        return None
    s = doi.strip().lower()
    # 去掉 URL 前缀
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"^doi:\s*", "", s)
    # 去尾部标点
    s = s.rstrip(".,;)")
    # 校验格式：10.NNNN/xxxx
    if re.match(r"^10\.\d{4,9}/.+", s):
        return s
    return None


def deduplicate_citations(paper_id: int) -> Dict:
    """对一篇论文的 citations_v2 做 DOI 归一化与去重。

    Returns:
        {"paper_id": N, "total": N, "normalized": N, "duplicates_removed": N, "invalid_doi": N}
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT id, cited_doi, raw_reference FROM citations_v2 WHERE citing_paper_id = ?",
        (paper_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    seen_dois = set()
    duplicates = []
    invalid = []

    for r in rows:
        doi = r["cited_doi"]
        if doi:
            normalized = normalize_doi(doi)
            if not normalized:
                invalid.append(r["id"])
                continue
            if normalized != doi:
                # 更新为归一化后的 DOI
                conn_tmp = get_conn()
                conn_tmp.execute(
                    "UPDATE citations_v2 SET cited_doi = ? WHERE id = ?",
                    (normalized, r["id"]),
                )
                conn_tmp.commit()
                conn_tmp.close()
            if normalized in seen_dois:
                duplicates.append(r["id"])
            else:
                seen_dois.add(normalized)
        # 没有 DOI 的暂不处理（留待模糊匹配）

    # 删除重复项
    if duplicates:
        conn = get_conn()
        for cid in duplicates:
            conn.execute("DELETE FROM citations_v2 WHERE id = ?", (cid,))
        conn.commit()
        conn.close()

    log.info(f"[dedup] paper_id={paper_id}: 总 {len(rows)} 条, "
             f"归一化 {len(rows) - len(invalid)}, "
             f"去重 {len(duplicates)}, 无效 DOI {len(invalid)}")

    return {
        "paper_id": paper_id,
        "total": len(rows),
        "normalized": len(rows) - len(invalid),
        "duplicates_removed": len(duplicates),
        "invalid_doi": len(invalid),
    }


# ============================================================
# 2. 引用网络基础统计
# ============================================================
def compute_network_stats() -> Dict:
    """计算整个引用网络的基础统计。

    Returns:
        {
            "total_papers": N, "total_citations": N,
            "unique_cited_dois": N,
            "avg_out_degree": float,
            "max_out_degree": {paper_id, count},
            "top_cited_papers": [(doi, in_degree), ...],  # 被引最多的论文
            "isolated_papers": N,
            "connected_components": N,
        }
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 总论文数
    cur.execute("SELECT COUNT(*) AS c FROM papers")
    total_papers = cur.fetchone()["c"]

    # 总引用数
    cur.execute("SELECT COUNT(*) AS c FROM citations_v2")
    total_citations = cur.fetchone()["c"]

    # 不同被引 DOI 数
    cur.execute("SELECT COUNT(DISTINCT cited_doi) AS c FROM citations_v2 WHERE cited_doi IS NOT NULL")
    unique_cited_dois = cur.fetchone()["c"]

    # 出度统计（每篇论文引用了多少）
    cur.execute(
        """SELECT citing_paper_id, COUNT(*) AS out_degree
           FROM citations_v2
           GROUP BY citing_paper_id
           ORDER BY out_degree DESC"""
    )
    out_degrees = [dict(r) for r in cur.fetchall()]

    avg_out = sum(o["out_degree"] for o in out_degrees) / len(out_degrees) if out_degrees else 0
    max_out = out_degrees[0] if out_degrees else None

    # 入度统计（每篇被引多少次）
    cur.execute(
        """SELECT cited_doi, COUNT(*) AS in_degree
           FROM citations_v2
           WHERE cited_doi IS NOT NULL
           GROUP BY cited_doi
           ORDER BY in_degree DESC
           LIMIT 20"""
    )
    top_cited = [(r["cited_doi"], r["in_degree"]) for r in cur.fetchall()]

    # 找出被引且在本库中的 DOI（连通性）
    cur.execute(
        """SELECT DISTINCT p.id
           FROM papers p
           JOIN citations_v2 c ON p.doi = c.cited_doi"""
    )
    internal_cited = set(r["id"] for r in cur.fetchall())

    # 引用了别的论文的论文
    citing_set = set(o["citing_paper_id"] for o in out_degrees)
    # 孤立论文：既不引用别人，也不被别人引用
    isolated = total_papers - len(citing_set | internal_cited)

    conn.close()

    log.info(f"[stats] 网络: {total_papers} 论文, {total_citations} 引用, "
             f"avg_out={avg_out:.2f}, top_cited={top_cited[0] if top_cited else None}")

    return {
        "total_papers": total_papers,
        "total_citations": total_citations,
        "unique_cited_dois": unique_cited_dois,
        "internal_cited_papers": len(internal_cited),
        "avg_out_degree": round(avg_out, 2),
        "max_out_degree": max_out,
        "top_cited_papers": top_cited,
        "isolated_papers": max(0, isolated),
    }


# ============================================================
# 3. 引用网络导出
# ============================================================
def export_to_gexf(output_path: Path) -> Dict:
    """导出 GEXF 格式（Gephi 可读）。

    节点：论文（id, doi, title）
    边：引用关系 (citing → cited)
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 取所有论文作为节点
    cur.execute("SELECT id, doi, title FROM papers")
    nodes = [dict(r) for r in cur.fetchall()]

    # 取所有引用作为边
    cur.execute(
        """SELECT citing_paper_id, cited_doi, match_confidence
           FROM citations_v2
           WHERE cited_doi IS NOT NULL"""
    )
    edges_raw = [dict(r) for r in cur.fetchall()]

    # 建立 DOI → paper_id 映射
    doi_to_id = {n["doi"]: n["id"] for n in nodes if n["doi"]}
    internal_edges = []
    external_dois = set()
    for e in edges_raw:
        cited_id = doi_to_id.get(e["cited_doi"])
        if cited_id:
            internal_edges.append({
                "source": e["citing_paper_id"],
                "target": cited_id,
                "confidence": e["match_confidence"],
            })
        else:
            external_dois.add(e["cited_doi"])
    conn.close()

    # 写 GEXF
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">')
    lines.append('  <meta><creator>literature-system</creator></meta>')
    lines.append('  <graph mode="static" defaultedgetype="directed">')

    # 节点
    lines.append('    <nodes>')
    for n in nodes:
        title = (n["title"] or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        doi = n["doi"] or ""
        lines.append(f'      <node id="{n["id"]}" label="{title[:60]}">')
        lines.append(f'        <attvalues>')
        lines.append(f'          <attvalue for="doi" value="{doi}"/>')
        lines.append(f'        </attvalues>')
        lines.append(f'      </node>')
    lines.append('    </nodes>')

    # 边
    lines.append('    <edges>')
    for i, e in enumerate(internal_edges):
        lines.append(f'      <edge id="{i}" source="{e["source"]}" target="{e["target"]}"/>')
    lines.append('    </edges>')

    lines.append('  </graph>')
    lines.append('</gexf>')

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"[gexf] 导出: {len(nodes)} 节点, {len(internal_edges)} 内部边, "
             f"{len(external_dois)} 外部 DOI")

    return {
        "nodes": len(nodes),
        "internal_edges": len(internal_edges),
        "external_dois": len(external_dois),
        "output_path": str(output_path),
    }


def export_to_csv(output_dir: Path) -> Dict:
    """导出 CSV 格式（nodes.csv + edges.csv）。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "citation_nodes.csv"
    edges_path = output_dir / "citation_edges.csv"

    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # nodes
    cur.execute("SELECT id, doi, title FROM papers")
    nodes = [dict(r) for r in cur.fetchall()]
    with nodes_path.open("w", encoding="utf-8") as f:
        f.write("id,doi,title\n")
        for n in nodes:
            title = (n["title"] or "").replace('"', '""')
            f.write(f'{n["id"]},"{n["doi"] or ""}","{title}"\n')

    # edges
    cur.execute(
        """SELECT citing_paper_id, cited_doi, match_method, match_confidence
           FROM citations_v2 WHERE cited_doi IS NOT NULL"""
    )
    edges = [dict(r) for r in cur.fetchall()]
    with edges_path.open("w", encoding="utf-8") as f:
        f.write("source_paper_id,cited_doi,match_method,match_confidence\n")
        for e in edges:
            f.write(f'{e["citing_paper_id"]},{e["cited_doi"]},'
                    f'{e["match_method"]},{e["match_confidence"]}\n')
    conn.close()

    log.info(f"[csv] 导出: {len(nodes)} 节点 → {nodes_path}, "
             f"{len(edges)} 边 → {edges_path}")

    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "nodes_path": str(nodes_path),
        "edges_path": str(edges_path),
    }


# ============================================================
# 4. 段落级引用追溯
# ============================================================
def trace_paragraph_citations(paper_id: int) -> Dict:
    """段落级引用追溯：找出每个章节的引用标注 → 关联到参考文献 → 被引论文 DOI。

    Returns:
        {
            "paper_id": N,
            "total_in_text_citations": N,
            "by_section": [{section_id, section_type, heading, citations: [...]}],
            "matched_to_cited_dois": N,
            "unmatched": N,
        }
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 取所有非 references 章节
    cur.execute(
        """SELECT id, section_type, heading, content, order_idx
           FROM paper_sections
           WHERE paper_id = ? AND section_type NOT IN ('references', 'acknowledgments')
           ORDER BY order_idx""",
        (paper_id,),
    )
    sections = [dict(r) for r in cur.fetchall()]

    # 2. 取已入库的参考文献
    cur.execute(
        """SELECT id, cited_doi, cited_title, cited_year, raw_reference, match_method
           FROM citations_v2 WHERE citing_paper_id = ?
           ORDER BY id""",
        (paper_id,),
    )
    refs = [dict(r) for r in cur.fetchall()]
    refs_by_id = {r["id"]: r for r in refs}
    refs_by_year = defaultdict(list)
    for r in refs:
        if r["cited_year"]:
            refs_by_year[r["cited_year"]].append(r)
    conn.close()

    # 3. 逐章节提取引用标注并追溯
    total_cites = 0
    matched_to_doi = 0
    unmatched = 0
    by_section = []

    for sec in sections:
        content = sec.get("content") or ""
        if not content:
            continue
        citations = extract_all_citations(content)

        # 追溯每条引用
        traced = []
        for c in citations:
            t = {
                "marker": c["marker"],
                "style": c["style"],
                "position": c["position_start"],
                "ref_id": None,
                "cited_doi": None,
                "cited_title": None,
                "traced": False,
            }
            if c["style"] == "ieee":
                ref_num = c.get("ref_number")
                if ref_num and ref_num in refs_by_id:
                    r = refs_by_id[ref_num]
                    t.update({
                        "ref_id": r["id"],
                        "cited_doi": r["cited_doi"],
                        "cited_title": (r["cited_title"] or "")[:80],
                        "traced": True,
                    })
            else:
                # APA：按年份找候选
                year = c.get("year")
                if year and year in refs_by_year:
                    candidates = refs_by_year[year]
                    if len(candidates) == 1:
                        r = candidates[0]
                        t.update({
                            "ref_id": r["id"],
                            "cited_doi": r["cited_doi"],
                            "cited_title": (r["cited_title"] or "")[:80],
                            "traced": True,
                        })
                    else:
                        # 多候选：标 ambiguous
                        t["traced"] = False
                        t["candidates"] = len(candidates)

            if t["traced"]:
                matched_to_doi += 1
            else:
                unmatched += 1
            traced.append(t)

        total_cites += len(citations)
        by_section.append({
            "section_id": sec["id"],
            "section_type": sec["section_type"],
            "heading": sec["heading"],
            "citation_count": len(citations),
            "citations": traced,
        })

    return {
        "paper_id": paper_id,
        "total_in_text_citations": total_cites,
        "matched_to_cited_dois": matched_to_doi,
        "unmatched": unmatched,
        "by_section": by_section,
        "refs_count": len(refs),
    }


# ============================================================
# 5. 模糊匹配（缺失 DOI 引用）
# ============================================================
def fuzzy_match_missing_doi(paper_id: int) -> Dict:
    """对缺失 DOI 的引用尝试模糊匹配。

    策略：用 (作者, 年份, 标题前缀) 在 papers 表中查找匹配。

    Returns:
        {"paper_id": N, "matched": N, "unmatched": N}
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """SELECT id, raw_reference, cited_year, cited_title
           FROM citations_v2
           WHERE citing_paper_id = ? AND cited_doi IS NULL
           AND (cited_year IS NOT NULL OR cited_title IS NOT NULL)""",
        (paper_id,),
    )
    unmatched_refs = [dict(r) for r in cur.fetchall()]

    matched = 0
    for ref in unmatched_refs:
        year = ref.get("cited_year")
        title = (ref.get("cited_title") or "").lower()
        if not year or not title:
            continue

        # 在 papers 表找同年份且标题前缀匹配
        cur.execute(
            """SELECT id, doi, title FROM papers
               WHERE published_date LIKE ? AND LOWER(title) LIKE ?
               LIMIT 1""",
            (f"%{year}%", f"%{title[:30]}%"),
        )
        m = cur.fetchone()
        if m:
            # 更新 citations_v2
            cur.execute(
                """UPDATE citations_v2
                   SET cited_doi = ?, match_method = 'fuzzy_match', match_confidence = 'medium'
                   WHERE id = ?""",
                (m["doi"], ref["id"]),
            )
            matched += 1
            log.info(f"[fuzzy] paper_id={paper_id}: 引用 {ref['id']} 模糊匹配到 DOI {m['doi']}")

    conn.commit()
    conn.close()

    log.info(f"[fuzzy] paper_id={paper_id}: 模糊匹配 {matched}/{len(unmatched_refs)}")
    return {
        "paper_id": paper_id,
        "matched": matched,
        "unmatched": len(unmatched_refs) - matched,
    }


if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))

    # 自测：用已有数据测试
    from pdf.pipeline import MineruAPIClient
    from pdf.ref_parser import extract_and_save_references

    PDF = Path(__file__).parent.parent / "pdfs" / "10.3897_arphapreprints.e142608.pdf"
    DOI = "10.3897/arphapreprints.e142608"
    MINERU_OUT = Path(__file__).parent / "test" / "marker_gpu_test" / "mineru_doi_output"

    # 准备测试数据
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
    cur.execute("DELETE FROM citations_v2 WHERE citing_paper_id = 999")

    # 插入 paper + sections + references
    cur.execute(
        "INSERT INTO papers (id, doi, title) VALUES (?, ?, ?)",
        (999, DOI, "Test paper"),
    )
    for sec in result.sections:
        cur.execute(
            """INSERT INTO paper_sections (paper_id, section_type, heading, content, page_start, page_end, order_idx)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (999, sec["section_type"], sec["heading"], sec.get("content", ""),
             sec.get("page_start"), sec.get("page_end"), sec["order_idx"]),
        )
    conn.commit()
    conn.close()

    # 提取参考文献
    ref_text = ""
    for sec in result.sections:
        if sec["section_type"] == "references":
            ref_text = sec["content"]
            break
    extract_and_save_references(999, DOI, ref_text, doi_lookup_limit=5)

    # 测试各种功能
    print("=" * 60)
    print("【1. DOI 归一化与去重】")
    print("=" * 60)
    dedup_stats = deduplicate_citations(999)
    print(json.dumps(dedup_stats, indent=2))

    print("\n" + "=" * 60)
    print("【2. 段落级引用追溯】")
    print("=" * 60)
    trace_stats = trace_paragraph_citations(999)
    print(f"总引用标注: {trace_stats['total_in_text_citations']}")
    print(f"追溯到参考文献: {trace_stats['matched_to_cited_dois']}")
    print(f"未匹配: {trace_stats['unmatched']}")
    print(f"参考文献总数: {trace_stats['refs_count']}")
    print("\n各章节引用分布:")
    for s in trace_stats["by_section"]:
        if s["citation_count"] > 0:
            print(f"  [{s['section_type']}] {s['heading'][:40]}: {s['citation_count']} 条")

    print("\n" + "=" * 60)
    print("【3. 引用网络基础统计】")
    print("=" * 60)
    net_stats = compute_network_stats()
    print(json.dumps(net_stats, indent=2, default=str))

    print("\n" + "=" * 60)
    print("【4. 网络导出 CSV】")
    print("=" * 60)
    csv_stats = export_to_csv(Path(__file__).parent / "test" / "citation_network")
    print(json.dumps(csv_stats, indent=2))

    print("\n" + "=" * 60)
    print("【5. 网络导出 GEXF】")
    print("=" * 60)
    gexf_stats = export_to_gexf(Path(__file__).parent / "test" / "citation_network" / "citation_network.gexf")
    print(json.dumps(gexf_stats, indent=2))

    # 清理
    conn = get_conn()
    conn.execute("DELETE FROM papers WHERE id = 999")
    conn.execute("DELETE FROM paper_fulltext WHERE paper_id = 999")
    conn.execute("DELETE FROM paper_sections WHERE paper_id = 999")
    conn.execute("DELETE FROM citations_v2 WHERE citing_paper_id = 999")
    conn.commit()
    conn.close()
    print("\n已清理测试数据")
