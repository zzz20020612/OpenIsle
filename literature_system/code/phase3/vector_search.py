"""向量检索与相似推荐（3.4）。

使用 sqlite-vec 扩展做 KNN 向量检索。
支持：
- 向量相似度检索（纯语义检索）
- 混合检索（FTS5 关键词 + 向量语义，融合排序）
- 相似论文推荐
- 跨论文知识对比
"""
from __future__ import annotations

import json
import struct
from typing import Any, Dict, List, Optional, Tuple

import config
from db import get_connection
from logger import get_logger

logger = get_logger("phase3.vector_search")


# ============================================================
# 向量检索
# ============================================================

def vector_search(
    query: str,
    *,
    top_k: Optional[int] = None,
    chunk_type: Optional[str] = None,
    paper_id: Optional[int] = None,
    embedding_client=None,
) -> List[Dict[str, Any]]:
    """向量相似度检索（纯语义检索）。

    Args:
        query: 查询文本
        top_k: 返回结果数（默认 config.VECTOR_SEARCH_TOP_K）
        chunk_type: 限制 chunk 类型（section/claim/method/data_point/abstract）
        paper_id: 限制论文 ID
        embedding_client: EmbeddingClient 实例

    Returns:
        结果列表，每个结果含：
        - paper_id, chunk_type, chunk_id, distance, text, metadata
    """
    if embedding_client is None:
        from .llm_client import EmbeddingClient
        embedding_client = EmbeddingClient()

    top_k = top_k or config.VECTOR_SEARCH_TOP_K

    # 生成查询向量
    query_embedding = embedding_client.embed_single(query)
    query_blob = _floats_to_blob(query_embedding)

    # 用 sqlite-vec 做 KNN 查询
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        # 加载 sqlite-vec 扩展
        loaded = _load_vec_extension_safe(conn)
        if not loaded:
            # sqlite-vec 不可用时，回退到 NumPy 余弦相似度
            logger.warning("sqlite-vec 不可用，回退到 NumPy 余弦相似度")
            return _numpy_search(query_embedding, top_k, chunk_type, paper_id)

        cur = conn.cursor()
        # 构建 KNN 查询
        # vec_distance_cosine 返回的是距离（0=完全相同，2=完全相反）
        # 转换为相似度：similarity = 1 - distance/2
        sql = (
            "SELECT e.paper_id, e.chunk_type, e.chunk_id, "
            "vec_distance_cosine(e.embedding, ?) AS distance "
            "FROM paper_embeddings e "
        )
        params: list = [query_blob]
        where_clauses = []
        if chunk_type:
            where_clauses.append("e.chunk_type=?")
            params.append(chunk_type)
        if paper_id:
            where_clauses.append("e.paper_id=?")
            params.append(paper_id)
        if where_clauses:
            sql += "WHERE " + " AND ".join(where_clauses) + " "
        sql += "ORDER BY distance ASC LIMIT ?"
        params.append(top_k)

        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    # 补充 chunk 文本和元数据
    results: List[Dict[str, Any]] = []
    for row in rows:
        paper_id_r, chunk_type_r, chunk_id_r, distance = row
        similarity = 1.0 - (distance / 2.0)
        text, metadata = _get_chunk_text(paper_id_r, chunk_type_r, chunk_id_r)
        results.append({
            "paper_id": paper_id_r,
            "chunk_type": chunk_type_r,
            "chunk_id": chunk_id_r,
            "distance": distance,
            "similarity": similarity,
            "text": text,
            "metadata": metadata,
        })

    return results


def _load_vec_extension_safe(conn) -> bool:
    """安全加载 sqlite-vec 扩展。"""
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception as e:
        logger.debug("sqlite-vec 加载失败（回退到 NumPy）: %s", e)
        return False


def _floats_to_blob(embedding: List[float]) -> bytes:
    """将 float 列表转为 BLOB。"""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _blob_to_floats(blob: bytes) -> List[float]:
    """BLOB 转 float 列表。"""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


# ============================================================
# NumPy 回退方案
# ============================================================

def _numpy_search(
    query_embedding: List[float],
    top_k: int,
    chunk_type: Optional[str],
    paper_id: Optional[int],
) -> List[Dict[str, Any]]:
    """NumPy 余弦相似度检索（sqlite-vec 不可用时的回退方案）。"""
    try:
        import numpy as np
    except ImportError:
        logger.error("NumPy 未安装，无法执行向量检索")
        return []

    query_vec = np.array(query_embedding, dtype=np.float32)
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []
    query_vec = query_vec / query_norm

    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        sql = "SELECT paper_id, chunk_type, chunk_id, embedding FROM paper_embeddings"
        where_clauses = []
        params: list = []
        if chunk_type:
            where_clauses.append("chunk_type=?")
            params.append(chunk_type)
        if paper_id:
            where_clauses.append("paper_id=?")
            params.append(paper_id)
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    # 计算余弦相似度
    scored: List[Tuple[float, tuple]] = []
    for row in rows:
        paper_id_r, chunk_type_r, chunk_id_r, blob = row
        vec = np.array(_blob_to_floats(blob), dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            continue
        vec = vec / norm
        similarity = float(np.dot(query_vec, vec))
        scored.append((similarity, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    results: List[Dict[str, Any]] = []
    for similarity, row in top:
        paper_id_r, chunk_type_r, chunk_id_r, _ = row
        text, metadata = _get_chunk_text(paper_id_r, chunk_type_r, chunk_id_r)
        results.append({
            "paper_id": paper_id_r,
            "chunk_type": chunk_type_r,
            "chunk_id": chunk_id_r,
            "distance": 2.0 * (1.0 - similarity),
            "similarity": similarity,
            "text": text,
            "metadata": metadata,
        })

    return results


# ============================================================
# Chunk 文本获取
# ============================================================

def _get_chunk_text(
    paper_id: int, chunk_type: str, chunk_id: int,
) -> Tuple[str, Dict[str, Any]]:
    """根据 chunk_type 和 chunk_id 获取 chunk 文本和元数据。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        if chunk_type == "section":
            cur.execute(
                "SELECT section_type, heading, content, page_start, page_end "
                "FROM paper_sections WHERE id=?",
                (chunk_id,),
            )
            row = cur.fetchone()
            if row:
                r = dict(row)
                return (
                    r.get("content", ""),
                    {"section_type": r.get("section_type"), "heading": r.get("heading"),
                     "page": f"{r.get('page_start')}-{r.get('page_end')}"},
                )
        elif chunk_type == "claim":
            cur.execute(
                "SELECT key_claims FROM paper_knowledge_cards WHERE paper_id=?",
                (paper_id,),
            )
            row = cur.fetchone()
            if row:
                claims = row["key_claims"]
                if isinstance(claims, str):
                    claims = json.loads(claims)
                if 0 < chunk_id <= len(claims):
                    claim = claims[chunk_id - 1]
                    return (
                        claim.get("claim", ""),
                        {"evidence": claim.get("evidence"), "condition": claim.get("condition")},
                    )
        elif chunk_type == "method":
            cur.execute(
                "SELECT methodology, workflow, data_sources "
                "FROM paper_methods WHERE paper_id=?",
                (paper_id,),
            )
            row = cur.fetchone()
            if row:
                r = dict(row)
                return (
                    r.get("methodology", ""),
                    {"workflow": r.get("workflow"), "data_sources": r.get("data_sources")},
                )
        elif chunk_type == "data_point":
            cur.execute(
                "SELECT metric_name, metric_value, unit, context, significance "
                "FROM paper_data_points WHERE id=?",
                (chunk_id,),
            )
            row = cur.fetchone()
            if row:
                r = dict(row)
                return (
                    f"{r.get('metric_name', '')} = {r.get('metric_value', '')} {r.get('unit', '')}",
                    {"context": r.get("context"), "significance": r.get("significance")},
                )
        elif chunk_type == "abstract":
            cur.execute(
                "SELECT title, abstract FROM papers WHERE id=?",
                (paper_id,),
            )
            row = cur.fetchone()
            if row:
                r = dict(row)
                return (
                    r.get("abstract", ""),
                    {"title": r.get("title"), "source": "abstract"},
                )
    finally:
        conn.close()

    return "", {}


# ============================================================
# 相似论文推荐
# ============================================================

def find_similar_papers(
    paper_id: int,
    *,
    top_k: int = 5,
    embedding_client=None,
) -> List[Dict[str, Any]]:
    """查找与指定论文最相似的论文。

    Args:
        paper_id: 目标论文 ID
        top_k: 返回结果数
        embedding_client: EmbeddingClient 实例

    Returns:
        相似论文列表（含 similarity_score）
    """
    # 获取目标论文的所有向量，计算平均向量作为论文向量
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT embedding FROM paper_embeddings WHERE paper_id=? AND chunk_type='section'",
            (paper_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        logger.warning("paper_id=%d 无 section 向量", paper_id)
        return []

    try:
        import numpy as np
    except ImportError:
        logger.error("NumPy 未安装")
        return []

    # 计算论文平均向量
    vecs = [np.array(_blob_to_floats(r[0]), dtype=np.float32) for r in rows]
    paper_vec = np.mean(vecs, axis=0)
    paper_vec = paper_vec / np.linalg.norm(paper_vec)

    # 查找其他论文
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT paper_id FROM paper_embeddings "
            "WHERE paper_id != ? AND chunk_type='section'",
            (paper_id,),
        )
        other_papers = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    # 计算每个论文的平均向量与相似度
    scored: List[Tuple[float, int]] = []
    for other_id in other_papers:
        conn = get_connection(init_schema=False, row_factory=False)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT embedding FROM paper_embeddings "
                "WHERE paper_id=? AND chunk_type='section'",
                (other_id,),
            )
            other_rows = cur.fetchall()
        finally:
            conn.close()

        if not other_rows:
            continue
        other_vecs = [np.array(_blob_to_floats(r[0]), dtype=np.float32) for r in other_rows]
        other_vec = np.mean(other_vecs, axis=0)
        norm = np.linalg.norm(other_vec)
        if norm == 0:
            continue
        other_vec = other_vec / norm
        similarity = float(np.dot(paper_vec, other_vec))
        scored.append((similarity, other_id))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # 补充论文元数据
    results: List[Dict[str, Any]] = []
    for similarity, pid in top:
        conn = get_connection(init_schema=False, row_factory=True)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, doi, title, journal, published_date FROM papers WHERE id=?",
                (pid,),
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if row:
            r = dict(row)
            r["similarity"] = similarity
            results.append(r)

    return results


# ============================================================
# 混合检索（FTS5 + 向量）
# ============================================================

def hybrid_search(
    query: str,
    *,
    top_k: int = 10,
    fts_weight: float = 0.4,
    vector_weight: float = 0.6,
    chunk_type: Optional[str] = None,
    paper_id: Optional[int] = None,
    embedding_client=None,
) -> List[Dict[str, Any]]:
    """混合检索（FTS5 关键词 + 向量语义）。

    复用第二阶段 FTS5 索引，融合向量语义检索结果。

    Args:
        query: 查询文本
        top_k: 返回结果数
        fts_weight: FTS5 权重
        vector_weight: 向量权重
        chunk_type: 限制向量检索的 chunk 类型（section/claim/method/data_point）
        paper_id: 限制向量检索的论文 ID
        embedding_client: EmbeddingClient 实例

    Returns:
        融合排序后的结果列表
    """
    # 1. FTS5 检索（复用第二阶段）
    fts_results = _fts_search(query, top_k=top_k * 2)

    # 2. 向量检索（支持 chunk_type / paper_id 过滤）
    vec_results = vector_search(
        query, top_k=top_k * 2, chunk_type=chunk_type, paper_id=paper_id,
        embedding_client=embedding_client
    )

    # 3. 融合排序（归一化加权）
    # FTS5 用 bm25 分数（越小越好），向量用 similarity（越大越好）
    scores: Dict[Tuple[str, int], float] = {}

    # FTS5 结果：将 -bm25 归一化到 [0, 1]
    if fts_results:
        max_bm25 = max(abs(r.get("bm25", 0)) for r in fts_results) or 1.0
        for r in fts_results:
            key = ("paper", r["paper_id"])
            normalized = 1.0 - abs(r.get("bm25", 0)) / max_bm25
            scores[key] = scores.get(key, 0) + fts_weight * normalized

    # 向量结果：similarity 已在 [0, 1]
    for r in vec_results:
        key = ("paper", r["paper_id"])
        scores[key] = scores.get(key, 0) + vector_weight * r.get("similarity", 0)

    # 排序并取 top_k
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    # 补充论文元数据
    results: List[Dict[str, Any]] = []
    for (kind, pid), score in sorted_scores:
        conn = get_connection(init_schema=False, row_factory=True)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, doi, title, abstract, journal, published_date "
                "FROM papers WHERE id=?",
                (pid,),
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if row:
            r = dict(row)
            r["hybrid_score"] = round(score, 4)
            results.append(r)

    return results


def _fts_search(query: str, top_k: int = 20) -> List[Dict[str, Any]]:
    """FTS5 关键词检索（复用第二阶段 papers_fts 表）。"""
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        # 检查 papers_fts 表是否存在
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'"
        )
        if not cur.fetchone():
            return []

        cur.execute(
            "SELECT paper_id, bm25(papers_fts) AS bm25 "
            "FROM papers_fts WHERE papers_fts MATCH ? "
            "ORDER BY bm25 LIMIT ?",
            (query, top_k),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    return [{"paper_id": r[0], "bm25": r[1]} for r in rows]


# ============================================================
# 跨论文知识对比
# ============================================================

def compare_metric_across_papers(
    metric_name: str,
    *,
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """跨论文对比同一指标在不同研究中的数值。

    Args:
        metric_name: 指标名（如 yield / efficiency / reduction）
        top_k: 返回结果数

    Returns:
        [{"paper_id", "title", "metric_value", "unit", "context", ...}]
    """
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT d.paper_id, p.title, p.journal, p.published_date,
                      d.metric_name, d.metric_value, d.unit, d.context,
                      d.significance, d.confidence
               FROM paper_data_points d
               JOIN papers p ON d.paper_id = p.id
               WHERE d.metric_name LIKE ?
               ORDER BY d.paper_id
               LIMIT ?""",
            (f"%{metric_name}%", top_k),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
