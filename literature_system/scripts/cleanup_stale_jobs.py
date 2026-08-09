"""清理 StaleJob 失败任务。

将 status='failed' 且 error_class='StaleJob' 的记录标记为 archived，
避免在统计中重复显示。

用法：
    python scripts/cleanup_stale_jobs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加 code 目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from logger import get_logger

logger = get_logger("scripts.cleanup_stale_jobs")


def cleanup_stale_jobs(dry_run: bool = False):
    """清理 StaleJob 失败任务。

    Args:
        dry_run: 仅打印，不实际更新
    """
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()

        # 查询 StaleJob 失败任务
        cur.execute("""
            SELECT id, paper_id, stage, error_class, started_at
            FROM parse_jobs
            WHERE status = 'failed' AND error_class = 'StaleJob'
            ORDER BY started_at DESC
        """)
        jobs = [dict(r) for r in cur.fetchall()]

        logger.info(f"找到 {len(jobs)} 条 StaleJob 失败任务")

        if not jobs:
            logger.info("无需清理")
            return

        if dry_run:
            for job in jobs[:10]:  # 只显示前10条
                logger.info(
                    f"[DRY-RUN] id={job['id']} paper_id={job['paper_id']} "
                    f"stage={job['stage']} started_at={job['started_at']} "
                    f"finished_at={job.get('finished_at')}"
                )
            if len(jobs) > 10:
                logger.info(f"[DRY-RUN] ... 还有 {len(jobs) - 10} 条")
        else:
            # 将这些任务标记为 archived（或改为 permanent_failed）
            cur.execute("""
                UPDATE parse_jobs
                SET status = 'archived'
                WHERE status = 'failed' AND error_class = 'StaleJob'
            """)
            conn.commit()
            updated_count = cur.rowcount
            logger.info(f"清理完成：已归档 {updated_count} 条 StaleJob 记录")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理 StaleJob 失败任务")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不实际更新")
    args = parser.parse_args()

    cleanup_stale_jobs(dry_run=args.dry_run)
