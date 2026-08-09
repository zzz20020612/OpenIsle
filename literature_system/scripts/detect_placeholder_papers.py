"""
占位/主题漂移论文检测脚本

检测逻辑：
1. 提取论文标题和摘要
2. 提取知识卡片中的 core_answer 和 key_claims
3. 使用 embedding 模型计算标题与提取内容的相似度
4. 相似度低于阈值（默认 0.35）则标记为 is_placeholder=1

用法：
    python scripts/detect_placeholder_papers.py [--threshold 0.35] [--db PATH]
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

import config
from db import get_connection
from phase3.llm_client import EmbeddingClient
from logger import get_logger

logger = get_logger("detect_placeholder")


def detect_placeholder_papers(threshold: float = 0.35, db_path: str = None):
    """检测并标记占位/主题漂移论文"""
    if db_path:
        config.SQLITE_PATH = Path(db_path)
    
    conn = get_connection(init_schema=False, row_factory=True)
    
    # 获取所有有知识卡片的论文
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.title, p.abstract, 
               pkc.core_answer, pkc.key_claims, pkc.research_question
        FROM papers p
        JOIN paper_knowledge_cards pkc ON p.id = pkc.paper_id
        WHERE p.title IS NOT NULL AND p.title != ''
    """)
    
    papers = cur.fetchall()
    logger.info(f"找到 {len(papers)} 篇有知识卡片的论文")
    
    if not papers:
        logger.warning("无论文待检测")
        return
    
    # 初始化 embedding 客户端
    try:
        embedder = EmbeddingClient()
    except Exception as e:
        logger.error(f"Embedding 客户端初始化失败: {e}")
        logger.error("请检查 EMBEDDING_API_KEY 和 EMBEDDING_BASE_URL 配置")
        return
    
    placeholder_papers = []
    
    for i, paper in enumerate(papers, 1):
        paper_id = paper["id"]
        title = paper["title"] or ""
        abstract = paper["abstract"] or ""
        core_answer = paper["core_answer"] or ""
        research_question = paper["research_question"] or ""
        
        # 解析 key_claims
        key_claims = []
        if paper["key_claims"]:
            try:
                if isinstance(paper["key_claims"], str):
                    claims_data = json.loads(paper["key_claims"])
                else:
                    claims_data = paper["key_claims"]
                
                if isinstance(claims_data, list):
                    for claim in claims_data:
                        if isinstance(claim, dict):
                            key_claims.append(claim.get("claim", ""))
            except Exception as e:
                logger.warning(f"论文 {paper_id} key_claims 解析失败: {e}")
        
        # 构造标题文本
        title_text = f"{title}. {abstract[:200]}" if abstract else title
        
        # 构造提取内容文本
        extracted_parts = []
        if research_question:
            extracted_parts.append(research_question)
        if core_answer:
            extracted_parts.append(core_answer)
        extracted_parts.extend(key_claims[:5])  # 取前5条 claims
        
        extracted_text = " ".join(extracted_parts)
        
        if not title_text.strip() or not extracted_text.strip():
            logger.warning(f"论文 {paper_id} 文本为空，跳过")
            continue
        
        # 计算相似度
        try:
            embeddings = embedder.embed([title_text, extracted_text])
            if len(embeddings) != 2:
                logger.warning(f"论文 {paper_id} embedding 数量异常")
                continue
            
            # 计算余弦相似度
            similarity = cosine_similarity(embeddings[0], embeddings[1])
            
            logger.info(f"[{i}/{len(papers)}] 论文 {paper_id}: 相似度={similarity:.3f}")
            
            if similarity < threshold:
                placeholder_papers.append({
                    "paper_id": paper_id,
                    "title": title,
                    "similarity": similarity,
                    "research_question": research_question[:100],
                    "core_answer": core_answer[:100],
                    "key_claims_count": len(key_claims)
                })
                
                # 标记为占位论文
                conn.execute(
                    "UPDATE papers SET is_placeholder = 1 WHERE id = ?",
                    (paper_id,)
                )
                conn.commit()
                logger.warning(f"  ⚠️  论文 {paper_id} 标记为占位论文 (相似度={similarity:.3f})")
        
        except Exception as e:
            logger.error(f"论文 {paper_id} 检测失败: {e}")
            continue
    
    conn.close()
    
    # 输出统计
    logger.info("=" * 60)
    logger.info(f"检测完成: 共 {len(papers)} 篇论文")
    logger.info(f"占位论文: {len(placeholder_papers)} 篇 (阈值={threshold})")
    
    if placeholder_papers:
        logger.info("\n占位论文列表:")
        for p in placeholder_papers:
            logger.info(f"  - 论文 {p['paper_id']}: 相似度={p['similarity']:.3f}")
            logger.info(f"    标题: {p['title'][:80]}")
            logger.info(f"    研究问题: {p['research_question']}")
            logger.info(f"    核心回答: {p['core_answer']}")
            logger.info(f"    key_claims 数量: {p['key_claims_count']}")
            logger.info("")
    
    return placeholder_papers


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    if len(vec1) != len(vec2):
        raise ValueError("向量维度不匹配")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检测占位/主题漂移论文")
    parser.add_argument("--threshold", type=float, default=0.35, help="相似度阈值（默认 0.35）")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    args = parser.parse_args()
    
    detect_placeholder_papers(threshold=args.threshold, db_path=args.db)
