"""回填 paper_knowledge_cards.prompt_version 为 v1-{paper_type} 格式。

历史问题：
现有 33 条知识卡片的 prompt_version 均为 'v1'，无法区分 review / methodology / experimental / data_description 使用的不同模板。
extractor.py 已在 2026-08-01 修改为写入 v1-{paper_type} 格式，本脚本用于回填历史数据。

回填策略：
调用 phase3.paper_classifier.classify_paper() 对每篇论文进行分类，
并根据分类结果将 prompt_version 从 'v1' 更新为 'v1-{paper_type}'。
仅修改 prompt_version = 'v1' 的记录（不含已带类型后缀的）。

用法：
    python scripts/migrate_prompt_version_with_type.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加 code 目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from logger import get_logger
from phase3.paper_classifier import classify_paper

logger = get_logger("scripts.migrate_prompt_version_with_type")

PHASE3_PROMPT_VERSION = "v1"  # 与 config.PHASE3_PROMPT_VERSION 保持一致


def migrate(dry_run: bool = False) -> dict:
    """执行迁移。

    Args:
        dry_run: 仅打印，不实际更新

    Returns:
        迁移统计信息
    """
    stats = {
        "checked": 0,
        "updated": 0,
        "skipped_placeholder": 0,
        "skipped_already_typed": 0,
        "by_type": {},
    }

    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        # 查询所有 prompt_version = 'v1' 的非占位知识卡片
        cur.execute("""
            SELECT k.paper_id, k.prompt_version, p.title, p.abstract, p.keywords,
                   p.is_placeholder
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE k.prompt_version NOT LIKE '%-%'
        """)
        rows = cur.fetchall()

        logger.info(f"找到 {len(rows)} 条 prompt_version 不带类型后缀的知识卡片")
        stats["checked"] = len(rows)

        for r in rows:
            paper_id = r["paper_id"]
            is_placeholder = r["is_placeholder"] or 0

            if is_placeholder == 1:
                stats["skipped_placeholder"] += 1
                continue

            meta = {
                "id": paper_id,
                "title": r["title"] or "",
                "abstract": r["abstract"] or "",
                "keywords": r["keywords"] or "",
            }
            paper_type = classify_paper(meta)
            new_version = f"{PHASE3_PROMPT_VERSION}-{paper_type}"

            stats["by_type"][paper_type] = stats["by_type"].get(paper_type, 0) + 1

            logger.info(
                f"paper_id={paper_id} {r['prompt_version']!r} → {new_version!r} (title={r['title'][:40]!r})"
            )
            if not dry_run:
                conn.execute(
                    "UPDATE paper_knowledge_cards SET prompt_version = ? WHERE paper_id = ?",
                    (new_version, paper_id),
                )
                conn.commit()
                stats["updated"] += 1

        logger.info(
            f"{'[DRY-RUN] ' if dry_run else ''}迁移完成："
            f"检查 {stats['checked']} 条，"
            f"更新 {stats['updated']} 条，"
            f"占位跳过 {stats['skipped_placeholder']} 条，"
            f"按类型分布: {stats['by_type']}"
        )
    finally:
        conn.close()

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="回填 paper_knowledge_cards.prompt_version 为 v1-{paper_type} 格式"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不实际更新")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
