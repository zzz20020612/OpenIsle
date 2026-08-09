"""
学者画像与机构合作网络 API 实现。

复用 authors + paper_authors + papers 三张表，提供：
- 学者列表与检索
- 单学者画像（论文、合作者、机构、年份/期刊/关键词分布）
- 单学者合作网络
- 机构合作网络
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple


def _extract_year(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    m = re.match(r"(\d{4})", str(date_str))
    return int(m.group(1)) if m else None


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        return [x.strip() for x in re.split(r"[,;]", value) if x.strip()]
    return value


def _parse_affiliations(affiliation: Any) -> List[str]:
    """从 authors.affiliation JSON / current_affiliation 解析机构名列表。"""
    result: List[str] = []
    parsed = _safe_json_loads(affiliation)
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                name = item.get("name") or item.get("affiliation") or ""
            else:
                name = str(item)
            if name:
                result.append(name.strip())
    elif isinstance(parsed, dict):
        name = parsed.get("name") or parsed.get("affiliation") or ""
        if name:
            result.append(name.strip())
    return [a for a in result if a]


def _author_institutions(row: Dict[str, Any]) -> List[str]:
    """从作者行提取归一化后的机构名（去重）。"""
    from search.institution_normalizer import normalize_affiliations

    raw: List[str] = []
    if row.get("current_affiliation"):
        raw.append(row["current_affiliation"].strip())
    raw.extend(_parse_affiliations(row.get("affiliation")))
    return normalize_affiliations(raw)


def list_authors(conn, qs: Dict[str, List[str]]) -> Dict[str, Any]:
    q = (qs.get("q", [""])[0] or "").strip()
    affiliation = (qs.get("affiliation", [""])[0] or "").strip()
    try:
        limit = int(qs.get("limit", ["50"])[0])
        offset = int(qs.get("offset", ["0"])[0])
    except ValueError:
        limit, offset = 50, 0

    where_clauses = ["1=1"]
    params: List[Any] = []
    if q:
        where_clauses.append("(a.full_name LIKE ? OR a.given_name LIKE ? OR a.family_name LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if affiliation:
        where_clauses.append("(a.current_affiliation LIKE ? OR a.affiliation LIKE ?)")
        like = f"%{affiliation}%"
        params.extend([like, like])

    cur = conn.cursor()
    count_sql = f"""
        SELECT COUNT(DISTINCT a.id) AS c
        FROM authors a
        WHERE {' AND '.join(where_clauses)}
    """
    cur.execute(count_sql, params)
    total = cur.fetchone()["c"]

    sql = f"""
        SELECT a.id, a.orcid, a.given_name, a.family_name, a.full_name,
               a.current_affiliation, a.affiliation, a.total_publications, a.h_index,
               COUNT(pa.paper_id) AS paper_count
        FROM authors a
        LEFT JOIN paper_authors pa ON pa.author_id = a.id
        WHERE {' AND '.join(where_clauses)}
        GROUP BY a.id
        ORDER BY paper_count DESC, a.full_name ASC
        LIMIT ? OFFSET ?
    """
    cur.execute(sql, params + [limit, offset])
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["institutions"] = _author_institutions(r)

    return {"total": total, "limit": limit, "offset": offset, "authors": rows}


def get_author_profile(conn, author_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, orcid, given_name, family_name, full_name,
               current_affiliation, affiliation, total_publications,
               h_index, total_citations, meta_json
        FROM authors WHERE id = ?
    """, (author_id,))
    row = cur.fetchone()
    if not row:
        return None
    author = dict(row)
    author["institutions"] = _author_institutions(author)

    # 论文统计
    cur.execute("""
        SELECT COUNT(*) AS c, COALESCE(SUM(COALESCE(p.citation_count, 0)), 0) AS citations
        FROM paper_authors pa
        JOIN papers p ON p.id = pa.paper_id
        WHERE pa.author_id = ?
    """, (author_id,))
    stat = cur.fetchone()
    total_papers = stat["c"]
    total_citations = stat["citations"]

    # 年份分布
    cur.execute("""
        SELECT substr(p.published_date, 1, 4) AS year, COUNT(*) AS c
        FROM paper_authors pa
        JOIN papers p ON p.id = pa.paper_id
        WHERE pa.author_id = ? AND p.published_date IS NOT NULL
              AND substr(p.published_date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
        GROUP BY year
        ORDER BY year
    """, (author_id,))
    year_distribution = [dict(r) for r in cur.fetchall()]

    # 期刊分布
    cur.execute("""
        SELECT p.journal, COUNT(*) AS c
        FROM paper_authors pa
        JOIN papers p ON p.id = pa.paper_id
        WHERE pa.author_id = ? AND p.journal IS NOT NULL AND p.journal != ''
        GROUP BY p.journal
        ORDER BY c DESC
        LIMIT 10
    """, (author_id,))
    top_journals = [dict(r) for r in cur.fetchall()]

    # 关键词分布
    cur.execute("""
        SELECT p.keywords
        FROM paper_authors pa
        JOIN papers p ON p.id = pa.paper_id
        WHERE pa.author_id = ?
    """, (author_id,))
    keyword_counts: Counter = Counter()
    for r in cur.fetchall():
        for kw in _parse_keyword_row(r["keywords"]):
            keyword_counts[kw] += 1
    top_keywords = [{"keyword": k, "count": c} for k, c in keyword_counts.most_common(20)]

    # 主要合作者
    cur.execute("""
        SELECT a.id, a.full_name, COUNT(*) AS c
        FROM paper_authors pa1
        JOIN paper_authors pa2 ON pa2.paper_id = pa1.paper_id AND pa2.author_id != pa1.author_id
        JOIN authors a ON a.id = pa2.author_id
        WHERE pa1.author_id = ?
        GROUP BY a.id
        ORDER BY c DESC
        LIMIT 20
    """, (author_id,))
    coauthors = [dict(r) for r in cur.fetchall()]

    return {
        "author": author,
        "stats": {
            "total_papers": total_papers,
            "total_citations": total_citations,
            "year_distribution": year_distribution,
            "top_journals": top_journals,
            "top_keywords": top_keywords,
        },
        "coauthors": coauthors,
    }


def get_author_papers(conn, author_id: int, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) AS c
        FROM paper_authors pa
        JOIN papers p ON p.id = pa.paper_id
        WHERE pa.author_id = ?
    """, (author_id,))
    total = cur.fetchone()["c"]

    cur.execute("""
        SELECT p.id, p.doi, p.title, p.published_date, p.journal,
               p.author, p.keywords, p.source, p.citation_count, p.language,
               pa.author_order
        FROM paper_authors pa
        JOIN papers p ON p.id = pa.paper_id
        WHERE pa.author_id = ?
        ORDER BY p.published_date DESC NULLS LAST
        LIMIT ? OFFSET ?
    """, (author_id, limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["author"] = _safe_json_loads(r.get("author"))
        r["keywords"] = _safe_json_loads(r.get("keywords"))
        r["year"] = _extract_year(r.get("published_date"))

    return {"total": total, "limit": limit, "offset": offset, "papers": rows}


def get_paper_authors(conn, paper_id: int) -> Dict[str, Any]:
    """获取单篇论文的作者列表（含作者 ID、机构），用于论文详情页联动学者/机构网络。"""
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.full_name, a.orcid, a.current_affiliation, a.affiliation,
               pa.author_order
        FROM paper_authors pa
        JOIN authors a ON a.id = pa.author_id
        WHERE pa.paper_id = ?
        ORDER BY COALESCE(pa.author_order, 999), a.full_name
    """, (paper_id,))
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["institutions"] = _author_institutions(r)
    return {"paper_id": paper_id, "count": len(rows), "authors": rows}


def get_author_network(conn, author_id: int, max_nodes: int = 50) -> Dict[str, Any]:
    """构建以某学者为中心的合作网络（作者节点 + 机构节点）。"""
    cur = conn.cursor()
    # 获取该作者信息
    cur.execute("SELECT id, full_name, current_affiliation, affiliation FROM authors WHERE id = ?", (author_id,))
    center_row = cur.fetchone()
    if not center_row:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids: Set[str] = set()

    def add_author_node(aid: int, name: str, meta: Optional[Dict] = None, is_center: bool = False):
        nid = f"a{aid}"
        if nid in node_ids:
            return nid
        node_ids.add(nid)
        node = {"id": nid, "label": name or f"作者 {aid}", "type": "author", "author_id": aid, "is_center": is_center}
        if meta:
            node.update(meta)
        nodes.append(node)
        return nid

    # 中心节点
    center_meta = dict(center_row)
    center_institutions = _author_institutions(center_meta)
    add_author_node(author_id, center_meta["full_name"], {"institutions": center_institutions}, is_center=True)

    # 合作边：作者两两之间
    cur.execute("""
        SELECT pa1.author_id AS a1, pa2.author_id AS a2, COUNT(*) AS w,
               a1.full_name AS n1, a2.full_name AS n2,
               a1.current_affiliation AS aff1, a1.affiliation AS aff1_json,
               a2.current_affiliation AS aff2, a2.affiliation AS aff2_json
        FROM paper_authors pa1
        JOIN paper_authors pa2 ON pa2.paper_id = pa1.paper_id AND pa1.author_id < pa2.author_id
        JOIN authors a1 ON a1.id = pa1.author_id
        JOIN authors a2 ON a2.id = pa2.author_id
        WHERE pa1.paper_id IN (
            SELECT paper_id FROM paper_authors WHERE author_id = ?
        )
        GROUP BY pa1.author_id, pa2.author_id
        ORDER BY w DESC
        LIMIT ?
    """, (author_id, max_nodes * 3))

    author_ids: Set[int] = {author_id}
    institution_counts: Counter = Counter()
    for r in cur.fetchall():
        a1, a2, w = r["a1"], r["a2"], r["w"]
        author_ids.add(a1)
        author_ids.add(a2)
        add_author_node(a1, r["n1"], {"institutions": _author_institutions({"current_affiliation": r["aff1"], "affiliation": r["aff1_json"]})})
        add_author_node(a2, r["n2"], {"institutions": _author_institutions({"current_affiliation": r["aff2"], "affiliation": r["aff2_json"]})})
        edges.append({"source": f"a{a1}", "target": f"a{a2}", "type": "coauthored", "weight": w})
        for inst in _author_institutions({"current_affiliation": r["aff1"], "affiliation": r["aff1_json"]}):
            institution_counts[inst] += w
        for inst in _author_institutions({"current_affiliation": r["aff2"], "affiliation": r["aff2_json"]}):
            institution_counts[inst] += w

    # 限制节点数：保留合作最密切的作者
    if len(nodes) > max_nodes:
        # 保留中心节点 + 按边权重排序的其它作者
        center_node = next(n for n in nodes if n.get("is_center"))
        other_authors = [n for n in nodes if not n.get("is_center")]
        # 按与中心的共同论文数排序（通过 edges 推断）
        weight_by_author: Dict[int, int] = {}
        for e in edges:
            if e["source"] == f"a{author_id}":
                aid = int(e["target"][1:])
            elif e["target"] == f"a{author_id}":
                aid = int(e["source"][1:])
            else:
                continue
            weight_by_author[aid] = weight_by_author.get(aid, 0) + e["weight"]
        other_authors.sort(key=lambda n: weight_by_author.get(n["author_id"], 0), reverse=True)
        kept = other_authors[: max_nodes - 1]
        nodes = [center_node] + kept
        kept_ids = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in kept_ids and e["target"] in kept_ids]
        # 重新计算机构
        institution_counts = Counter()
        for n in nodes:
            for inst in n.get("institutions", []):
                institution_counts[inst] += 1

    # 添加机构节点与作者-机构边
    for inst, count in institution_counts.most_common(max(5, max_nodes - len(nodes))):
        inst_slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', inst).strip('_')[:60]
        iid = f"i{inst_slug}"
        if iid in node_ids:
            continue
        node_ids.add(iid)
        nodes.append({"id": iid, "label": inst, "type": "institution", "paper_count": count})
        # 连接该机构下的作者
        for n in nodes:
            if n["type"] != "author":
                continue
            if inst in n.get("institutions", []):
                edges.append({"source": n["id"], "target": iid, "type": "affiliated_with"})

    # 机构-机构合作边（基于同一篇论文的机构共现）
    if len(node_ids) < max_nodes:
        cur.execute("""
            SELECT pa.paper_id, a.current_affiliation, a.affiliation
            FROM paper_authors pa
            JOIN authors a ON a.id = pa.author_id
            WHERE pa.paper_id IN (
                SELECT paper_id FROM paper_authors WHERE author_id = ?
            )
        """, (author_id,))
        paper_insts: Dict[int, Set[str]] = {}
        for r in cur.fetchall():
            insts = _author_institutions(dict(r))
            if insts:
                paper_insts.setdefault(r["paper_id"], set()).update(insts)

        inst_node_map = {n["label"]: n["id"] for n in nodes if n["type"] == "institution"}
        inst_pair_counts: Counter = Counter()
        for insts in paper_insts.values():
            present = [i for i in insts if i in inst_node_map]
            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    inst_pair_counts[tuple(sorted([present[i], present[j]]))] += 1
        for (i1, i2), c in inst_pair_counts.items():
            if c < 1:
                continue
            edges.append({"source": inst_node_map[i1], "target": inst_node_map[i2], "type": "institution_collab", "weight": c})

    return {
        "center_author_id": author_id,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


def get_institution_network(conn, affiliation: Optional[str] = None,
                            max_nodes: int = 60, min_papers: int = 1) -> Dict[str, Any]:
    """构建机构合作网络。

    若传入 affiliation，则聚焦该机构及其直接合作机构；否则返回全局前 N 机构网络。
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT pa.paper_id, a.current_affiliation, a.affiliation
        FROM paper_authors pa
        JOIN authors a ON a.id = pa.author_id
        WHERE a.current_affiliation IS NOT NULL OR a.affiliation IS NOT NULL
    """)

    # paper_id -> list of institutions
    paper_insts: Dict[int, Set[str]] = {}
    institution_counts: Counter = Counter()
    for r in cur.fetchall():
        insts = _author_institutions(dict(r))
        if not insts:
            continue
        paper_insts.setdefault(r["paper_id"], set()).update(insts)
        for inst in insts:
            institution_counts[inst] += 1

    if affiliation:
        query = affiliation.lower()
        matched = {inst for inst in institution_counts if query in inst.lower()}
        if not matched:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0, "query": affiliation}
        # 选取最匹配的一个作为中心
        center = sorted(matched, key=lambda x: institution_counts[x], reverse=True)[0]
        # 收集与中心机构共现过的机构
        neighbor_counts: Counter = Counter()
        for insts in paper_insts.values():
            if center not in insts:
                continue
            for inst in insts:
                if inst != center:
                    neighbor_counts[inst] += 1
        selected = {center}
        selected.update([inst for inst, _ in neighbor_counts.most_common(max_nodes - 1)])
    else:
        selected = {inst for inst, _ in institution_counts.most_common(max_nodes)}

    selected = {inst for inst in selected if institution_counts[inst] >= min_papers}
    if not selected:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0, "query": affiliation}

    # 构建机构间边
    pair_counts: Counter = Counter()
    for insts in paper_insts.values():
        present = [i for i in insts if i in selected]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                pair_counts[tuple(sorted([present[i], present[j]]))] += 1

    nodes: List[Dict[str, Any]] = []
    node_map: Dict[str, str] = {}
    for inst in selected:
        inst_slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', inst).strip('_')[:60]
        iid = f"i{inst_slug}"
        # 处理冲突（同名简化后可能相同）
        base = iid
        suffix = 2
        while iid in node_map.values():
            iid = f"{base}_{suffix}"
            suffix += 1
        node_map[inst] = iid
        nodes.append({
            "id": iid,
            "label": inst,
            "type": "institution",
            "paper_count": institution_counts[inst],
            "is_center": bool(affiliation and inst == center),
        })

    edges: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str]] = set()
    for (i1, i2), c in pair_counts.items():
        s, t = node_map[i1], node_map[i2]
        key = tuple(sorted([s, t]))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append({"source": s, "target": t, "type": "institution_collab", "weight": c})

    return {
        "query": affiliation,
        "center": center if affiliation else None,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


def _parse_keyword_row(value: Any) -> List[str]:
    parsed = _safe_json_loads(value)
    if isinstance(parsed, list):
        return [str(x).strip() for x in parsed if str(x).strip()]
    if isinstance(parsed, str):
        return [parsed.strip()] if parsed.strip() else []
    return []
