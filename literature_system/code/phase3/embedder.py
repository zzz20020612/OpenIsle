"""向量化模块（3.4）。

复用第二阶段 paper_sections.content 作为 chunk，避免重新切分全文。
chunk_type 分四类：
- section: chunk_id 指向 paper_sections.id（直接用章节作 chunk）
- claim: chunk_id 指向 paper_knowledge_cards.key_claims[i]（用 paper_id + index 编码）
- method: chunk_id 指向 paper_methods.paper_id
- data_point: chunk_id 指向 paper_data_points.id

向量存储：使用 sqlite-vec 扩展做 KNN 查询。
"""
from __future__ import annotations

import json
import struct
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import config
from db import get_connection
from logger import get_logger

logger = get_logger("phase3.embedder")

# sqlite-vec 扩展加载状态
_vec_extension_loaded: bool = False


def _load_vec_extension(conn) -> bool:
    """加载 sqlite-vec 扩展。

    Returns:
        True 加载成功，False 加载失败（sqlite-vec 未安装）
    """
    global _vec_extension_loaded
    if _vec_extension_loaded:
        return True

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        _vec_extension_loaded = True
        logger.info("sqlite-vec 扩展加载成功")
        return True
    except ImportError:
        logger.warning(
            "sqlite-vec 未安装。请运行 pip install sqlite-vec。"
            "向量化功能将不可用，但其他功能不受影响。"
        )
        return False
    except Exception as e:
        logger.warning("sqlite-vec 扩展加载失败: %s", e)
        return False


def _floats_to_blob(embedding: List[float]) -> bytes:
    """将 float 列表转为 SQLite BLOB（float32 二进制格式）。"""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _blob_to_floats(blob: bytes) -> List[float]:
    """将 BLOB 转回 float 列表。"""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


# ============================================================
# Chunk 构建
# ============================================================

def collect_chunks(paper_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """收集待向量化的 chunk（复用第二阶段 paper_sections.content）。

    Args:
        paper_id: 指定论文 ID，None 收集全部

    Returns:
        chunk 列表，每个 chunk 含：
        - paper_id, chunk_type, chunk_id, text
    """
    chunks: List[Dict[str, Any]] = []
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()

        # 1. section chunk（复用 paper_sections.content）
        if paper_id:
            cur.execute(
                "SELECT id, paper_id, section_type, heading, content "
                "FROM paper_sections WHERE paper_id=? AND content IS NOT NULL AND content!=''",
                (paper_id,),
            )
        else:
            cur.execute(
                "SELECT id, paper_id, section_type, heading, content "
                "FROM paper_sections WHERE content IS NOT NULL AND content!=''",
            )
        for row in cur.fetchall():
            r = dict(row)
            text = f"[{r['section_type']}] {r.get('heading', '')}\n{r['content']}"
            chunks.append({
                "paper_id": r["paper_id"],
                "chunk_type": "section",
                "chunk_id": r["id"],
                "text": text,
            })

        # 2. claim chunk（从 paper_knowledge_cards.key_claims 提取）
        if paper_id:
            cur.execute(
                "SELECT paper_id, key_claims FROM paper_knowledge_cards WHERE paper_id=?",
                (paper_id,),
            )
        else:
            cur.execute("SELECT paper_id, key_claims FROM paper_knowledge_cards")
        for row in cur.fetchall():
            r = dict(row)
            claims = r.get("key_claims", [])
            if isinstance(claims, str):
                claims = json.loads(claims)
            for i, claim in enumerate(claims):
                if isinstance(claim, dict):
                    text = f"[claim] {claim.get('claim', '')} evidence: {claim.get('evidence', '')}"
                    chunks.append({
                        "paper_id": r["paper_id"],
                        "chunk_type": "claim",
                        "chunk_id": i + 1,  # claim 用 1-based index
                        "text": text,
                    })

        # 3. method chunk（从 paper_methods 提取）
        if paper_id:
            cur.execute(
                "SELECT paper_id, methodology, workflow, data_sources, models_algorithms "
                "FROM paper_methods WHERE paper_id=?",
                (paper_id,),
            )
        else:
            cur.execute(
                "SELECT paper_id, methodology, workflow, data_sources, models_algorithms "
                "FROM paper_methods",
            )
        for row in cur.fetchall():
            r = dict(row)
            text_parts = [f"[method] {r.get('methodology', '')}"]
            for field in ["workflow", "data_sources", "models_algorithms"]:
                val = r.get(field, "")
                if val:
                    if isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except json.JSONDecodeError:
                            pass
                    text_parts.append(f"{field}: {json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val}")
            chunks.append({
                "paper_id": r["paper_id"],
                "chunk_type": "method",
                "chunk_id": r["paper_id"],  # method 用 paper_id 作 chunk_id
                "text": "\n".join(text_parts),
            })

        # 4. data_point chunk（从 paper_data_points 提取）
        if paper_id:
            cur.execute(
                "SELECT id, paper_id, metric_name, metric_value, unit, context, significance "
                "FROM paper_data_points WHERE paper_id=?",
                (paper_id,),
            )
        else:
            cur.execute(
                "SELECT id, paper_id, metric_name, metric_value, unit, context, significance "
                "FROM paper_data_points",
            )
        for row in cur.fetchall():
            r = dict(row)
            text = (
                f"[data_point] {r.get('metric_name', '')}={r.get('metric_value', '')} "
                f"{r.get('unit', '')} (significance: {r.get('significance', '')}) "
                f"context: {r.get('context', '')}"
            )
            chunks.append({
                "paper_id": r["paper_id"],
                "chunk_type": "data_point",
                "chunk_id": r["id"],
                "text": text,
            })

    finally:
        conn.close()

    # 5. abstract chunk（无 section/claim/method/data_point 的兜底）
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        if paper_id:
            cur.execute(
                "SELECT id, title, abstract FROM papers WHERE id=? AND COALESCE(abstract, '')!=''",
                (paper_id,),
            )
        else:
            cur.execute(
                """
                SELECT p.id, p.title, p.abstract FROM papers p
                WHERE COALESCE(p.abstract, '') != ''
                AND NOT EXISTS (SELECT 1 FROM paper_sections ps WHERE ps.paper_id = p.id)
                AND NOT EXISTS (SELECT 1 FROM paper_knowledge_cards pkc WHERE pkc.paper_id = p.id)
                AND NOT EXISTS (SELECT 1 FROM paper_methods pm WHERE pm.paper_id = p.id)
                AND NOT EXISTS (SELECT 1 FROM paper_data_points pdp WHERE pdp.paper_id = p.id)
                """
            )
        for row in cur.fetchall():
            r = dict(row)
            text = f"[abstract] {r.get('title', '')}\n{r.get('abstract', '')}"
            chunks.append({
                "paper_id": r["id"],
                "chunk_type": "abstract",
                "chunk_id": r["id"],
                "text": text,
            })
    finally:
        conn.close()

    logger.info("收集到 %d 个 chunk（paper_id=%s）", len(chunks), paper_id or "all")
    return chunks


# ============================================================
# 向量化
# ============================================================

def embed_chunks(
    chunks: List[Dict[str, Any]],
    embedding_client=None,
) -> int:
    """批量向量化 chunk 并存入 paper_embeddings 表。

    Args:
        chunks: collect_chunks() 返回的 chunk 列表
        embedding_client: EmbeddingClient 实例（None 时自动创建）

    Returns:
        成功向量化的 chunk 数量
    """
    if not chunks:
        logger.warning("无 chunk 待向量化")
        return 0

    if embedding_client is None:
        from .llm_client import EmbeddingClient
        embedding_client = EmbeddingClient()

    # 过滤已向量化的 chunk（避免重复）
    new_chunks = _filter_unembedded(chunks)
    if not new_chunks:
        logger.info("所有 chunk 已向量化，跳过")
        return 0

    logger.info("开始向量化 %d 个 chunk（模型=%s）", len(new_chunks), embedding_client.model)

    # 批量生成向量
    texts = [c["text"] for c in new_chunks]
    try:
        embeddings = embedding_client.embed(texts)
    except Exception as e:
        logger.error("向量化失败: %s", e)
        raise

    if len(embeddings) != len(new_chunks):
        logger.error(
            "向量数量不匹配: chunks=%d embeddings=%d", len(new_chunks), len(embeddings)
        )
        return 0

    # 存入数据库
    embedded_at = datetime.now().isoformat()
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        for chunk, embedding in zip(new_chunks, embeddings):
            conn.execute(
                """INSERT OR REPLACE INTO paper_embeddings
                   (paper_id, chunk_type, chunk_id, embedding, model_name, embedded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    chunk["paper_id"],
                    chunk["chunk_type"],
                    chunk["chunk_id"],
                    _floats_to_blob(embedding),
                    embedding_client.model,
                    embedded_at,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    logger.info("向量化完成 %d 个 chunk", len(new_chunks))
    return len(new_chunks)


def embed_paper(
    paper_id: int,
    embedding_client=None,
    *,
    force: bool = False,
) -> int:
    """向量化单篇论文的全部 chunk。

    Args:
        paper_id: 论文 ID
        embedding_client: EmbeddingClient 实例
        force: 是否强制重新向量化

    Returns:
        成功向量化的 chunk 数量
    """
    if force:
        _delete_embeddings(paper_id)

    chunks = collect_chunks(paper_id)
    return embed_chunks(chunks, embedding_client)


def embed_batch(
    paper_ids: List[int],
    embedding_client=None,
    *,
    force: bool = False,
) -> Dict[int, int]:
    """批量向量化多篇论文。

    优化：先统一收集所有论文的 chunk，再一次性批量调用 embedding 接口，
    充分利用 EMBEDDING_BATCH_SIZE，减少网络往返。

    Returns:
        {paper_id: embedded_count}
    """
    if embedding_client is None:
        from .llm_client import EmbeddingClient
        embedding_client = EmbeddingClient()

    if force:
        for pid in paper_ids:
            _delete_embeddings(pid)

    # 1. 统一收集所有 chunk
    all_chunks: List[Dict[str, Any]] = []
    for pid in paper_ids:
        chunks = collect_chunks(pid)
        all_chunks.extend(chunks)

    # 2. 一次性批量向量化
    try:
        total_embedded = embed_chunks(all_chunks, embedding_client)
    except Exception as e:
        logger.error("批量向量化失败: %s", e)
        total_embedded = 0

    # 3. 统计每篇论文的向量化数量
    results: Dict[int, int] = {pid: 0 for pid in paper_ids}
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        placeholders = ",".join("?" * len(paper_ids))
        cur.execute(
            f"SELECT paper_id, COUNT(*) FROM paper_embeddings "
            f"WHERE paper_id IN ({placeholders}) GROUP BY paper_id",
            paper_ids,
        )
        for pid, count in cur.fetchall():
            results[pid] = count
    finally:
        conn.close()

    logger.info(
        "批量向量化完成: 论文 %d 篇, 总 chunk %d 个, 成功嵌入 %d 个",
        len(paper_ids),
        len(all_chunks),
        total_embedded,
    )
    return results


# ============================================================
# 内部工具
# ============================================================

def _filter_unembedded(chunks: List[Dict]) -> List[Dict]:
    """过滤出尚未向量化的 chunk。"""
    if not chunks:
        return []
    # 收集 (paper_id, chunk_type, chunk_id) 三元组
    keys = [(c["paper_id"], c["chunk_type"], c["chunk_id"]) for c in chunks]
    placeholders = ",".join(["(?, ?, ?)"] * len(keys))

    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        params = []
        for k in keys:
            params.extend(k)
        cur.execute(
            f"SELECT paper_id, chunk_type, chunk_id FROM paper_embeddings "
            f"WHERE (paper_id, chunk_type, chunk_id) IN ({placeholders})",
            params,
        )
        existing = {(r[0], r[1], r[2]) for r in cur.fetchall()}
    finally:
        conn.close()

    return [c for c in chunks if (c["paper_id"], c["chunk_type"], c["chunk_id"]) not in existing]


def _delete_embeddings(paper_id: int) -> None:
    """删除论文的向量数据。"""
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        conn.execute("DELETE FROM paper_embeddings WHERE paper_id=?", (paper_id,))
        conn.commit()
    finally:
        conn.close()


def get_embedding_stats() -> Dict[str, Any]:
    """获取向量化统计信息。"""
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM paper_embeddings")
        total = cur.fetchone()[0]
        cur.execute(
            "SELECT chunk_type, COUNT(*) FROM paper_embeddings GROUP BY chunk_type"
        )
        by_type = dict(cur.fetchall())
        cur.execute("SELECT COUNT(DISTINCT paper_id) FROM paper_embeddings")
        papers = cur.fetchone()[0]
        return {
            "total_embeddings": total,
            "by_chunk_type": by_type,
            "papers_with_embeddings": papers,
        }
    finally:
        conn.close()
