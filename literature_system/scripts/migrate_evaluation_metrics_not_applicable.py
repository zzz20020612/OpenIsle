"""回填 paper_methods.evaluation_metrics = 'not_applicable'。

对于非实验类论文（review / methodology / data_description），
若 evaluation_metrics 为空，写入 "not_applicable" 标记。

用法：
    python scripts/migrate_evaluation_metrics_not_applicable.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from logger import get_logger
from phase3.paper_classifier import classify_paper

logger = get_logger("scripts.migrate_evaluation_metrics")

NOT_APPLICABLE_PAPER_TYPES = {"review", "methodology", "data_description"}


def migrate(dry_run: bool = False) -> dict:
    """执行迁移。

    Returns:
        统计信息
    """
    stats = {
        "checked": 0,
        "marked": 0,
        "skipped_experimental": 0,
    }

    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.paper_id, p.title, p.abstract, p.keywords,
                   m.evaluation_metrics, p.is_placeholder
            FROM paper_methods m
            JOIN papers p ON p.id = m.paper_id
            WHERE (m.evaluation_metrics IS NULL
                   OR m.evaluation_metrics = ''
                   OR m.evaluation_metrics = '[]')
        """)
        rows = cur.fetchall()

        for r in rows:
            stats["checked"] += 1
            if r["is_placeholder"] == 1:
                continue  # 占位论文不动

            meta = {
                "id": r["paper_id"],
                "title": r["title"] or "",
                "abstract": r["abstract"] or "",
                "keywords": r["keywords"] or "",
            }
            paper_type = classify_paper(meta)

            if paper_type not in NOT_APPLICABLE_PAPER_TYPES:
                stats["skipped_experimental"] += 1
                continue

            logger.info(
                "paper_id=%d type=%s → evaluation_metrics = 'not_applicable'",
                r["paper_id"], paper_type
            )
            if not dry_run:
                conn.execute(
                    "UPDATE paper_methods SET evaluation_metrics = ? WHERE paper_id = ?",
                    ("not_applicable", r["paper_id"]),
                )
                conn.commit()
                stats["marked"] += 1

        logger.info(
            "{}迁移完成：检查 {} 篇，标记 {} 篇，跳过实验类 {} 篇".format(
                "[DRY-RUN] " if dry_run else "",
                stats["checked"], stats["marked"], stats["skipped_experimental"]
            )
        )
    finally:
        conn.close()

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="回填 paper_methods.evaluation_metrics = 'not_applicable'"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
