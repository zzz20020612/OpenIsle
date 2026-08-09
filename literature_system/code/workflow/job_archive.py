"""工作流任务归档与失败统计。

功能：
- 将长时间不活跃的 parse_jobs 记录迁移到 parse_jobs_archive，避免主表膨胀
- 按 error_class / stage / status 统计失败原因
- 获取单条 job 的重试/降级执行链
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from db import get_connection


def _iso_now() -> str:
    return datetime.now().isoformat()


def archive_old_jobs(
    days: int = 7,
    batch: int = 1000,
    conn: Optional[Any] = None,
) -> Dict[str, int]:
    """将 finished_at 超过 days 天的非 running 任务归档到 parse_jobs_archive。

    Args:
        days: 仅归档 finished_at 超过此天数的记录
        batch: 每批最大归档数量
        conn: 可选外部连接；None 则新建连接

    Returns:
        {"archived": int, "deleted": int}
    """
    close_conn = conn is None
    if conn is None:
        conn = get_connection(init_schema=False, row_factory=False)

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    try:
        cur = conn.cursor()
        # 选择待归档记录
        cur.execute(
            """SELECT id, paper_id, stage, status, parser_used, retry_count, max_retries,
                      parent_job_id, error_class, error_msg, mineru_task_id, started_at, finished_at
               FROM parse_jobs
               WHERE status != 'running' AND finished_at IS NOT NULL AND finished_at < ?
               ORDER BY id
               LIMIT ?""",
            (cutoff, batch),
        )
        rows = cur.fetchall()
        if not rows:
            return {"archived": 0, "deleted": 0}

        ids = [r[0] for r in rows]
        archived_at = _iso_now()
        archive_rows = [
            (
                r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                r[7], r[8], r[9], r[10], r[11], r[12], archived_at,
            )
            for r in rows
        ]

        cur.executemany(
            """INSERT INTO parse_jobs_archive
               (id, paper_id, stage, status, parser_used, retry_count, max_retries,
                parent_job_id, error_class, error_msg, mineru_task_id, started_at, finished_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            archive_rows,
        )
        placeholders = ",".join("?" * len(ids))
        cur.execute(
            f"DELETE FROM parse_jobs WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()
        return {"archived": len(rows), "deleted": cur.rowcount}
    finally:
        if close_conn:
            conn.close()


def get_failure_stats(conn: Optional[Any] = None) -> Dict[str, Any]:
    """返回失败原因分类统计。

    Returns:
        {
            "total_failed": int,
            "by_error_class": [{"error_class": str, "count": int}],
            "by_stage_status": [{"stage": str, "status": str, "count": int}],
        }
    """
    close_conn = conn is None
    if conn is None:
        conn = get_connection(init_schema=False, row_factory=True)

    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT error_class, COUNT(*) AS c
               FROM parse_jobs
               WHERE status IN ('failed', 'permanent_failed')
               GROUP BY error_class
               ORDER BY c DESC"""
        )
        by_error_class = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT stage, status, COUNT(*) AS c
               FROM parse_jobs
               WHERE status IN ('failed', 'permanent_failed')
               GROUP BY stage, status
               ORDER BY c DESC"""
        )
        by_stage_status = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT COUNT(*) AS c FROM parse_jobs
               WHERE status IN ('failed', 'permanent_failed')"""
        )
        total_failed = cur.fetchone()["c"]

        return {
            "total_failed": total_failed,
            "by_error_class": by_error_class,
            "by_stage_status": by_stage_status,
        }
    finally:
        if close_conn:
            conn.close()


def get_job_chain(job_id: int, conn: Optional[Any] = None) -> List[Dict[str, Any]]:
    """获取某条 job 的执行链（从根 job 到当前 job）。"""
    close_conn = conn is None
    if conn is None:
        conn = get_connection(init_schema=False, row_factory=True)

    try:
        cur = conn.cursor()
        chain = []
        current_id = job_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            cur.execute(
                """SELECT id, paper_id, stage, status, parser_used, parent_job_id,
                          error_class, error_msg, started_at, finished_at
                   FROM parse_jobs WHERE id = ?""",
                (current_id,),
            )
            row = cur.fetchone()
            if not row:
                break
            chain.append(dict(row))
            current_id = row["parent_job_id"]
        chain.reverse()
        return chain
    finally:
        if close_conn:
            conn.close()


def count_archived(conn: Optional[Any] = None) -> int:
    """返回归档表记录总数。"""
    close_conn = conn is None
    if conn is None:
        conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM parse_jobs_archive")
        return cur.fetchone()["c"]
    finally:
        if close_conn:
            conn.close()
