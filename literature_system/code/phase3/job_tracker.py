"""第三阶段 LLM 提取任务追踪。

将每篇论文的 3.1/3.2/3.3 提取状态写入 parse_jobs 表（stage='extract'，
parser_used 区分 knowledge_card / methods / data_points），便于：
- 工作流页面展示提取失败
- 自动重试仅针对失败/缺失的类型
- 统计覆盖率
"""
from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from db import get_connection


EXTRACTION_TYPES = ["knowledge_card", "methods", "data_points"]


def _iso_now() -> str:
    return datetime.now().isoformat()


def record_extraction_start(
    paper_id: int,
    extract_type: str,
    retry_count: int = 0,
    max_retries: int = 3,
    parent_job_id: Optional[int] = None,
) -> int:
    """记录一次提取开始，返回 job id。"""
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        now = _iso_now()
        cur.execute(
            """INSERT INTO parse_jobs
               (paper_id, stage, status, parser_used, retry_count, max_retries,
                parent_job_id, started_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paper_id, "extract", "running", extract_type, retry_count, max_retries,
             parent_job_id, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def record_extraction_status(
    paper_id: int,
    extract_type: str,
    status: str,
    error_msg: Optional[str] = None,
    error_class: Optional[str] = None,
    retry_count: int = 0,
    parent_job_id: Optional[int] = None,
) -> None:
    """记录一次提取最终状态（done / failed / skipped）。

    parent_job_id 仅在 status='running' 新建记录时写入，用于重试/降级链路追踪。
    """
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        if status == "running" and parent_job_id is not None:
            conn.execute(
                """INSERT INTO parse_jobs
                   (paper_id, stage, status, parser_used, retry_count,
                    parent_job_id, error_class, error_msg, started_at, finished_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper_id,
                    "extract",
                    status,
                    extract_type,
                    retry_count,
                    parent_job_id,
                    error_class,
                    error_msg,
                    _iso_now(),
                    _iso_now(),
                ),
            )
        else:
            conn.execute(
                """INSERT INTO parse_jobs
                   (paper_id, stage, status, parser_used, retry_count, error_class, error_msg, started_at, finished_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper_id,
                    "extract",
                    status,
                    extract_type,
                    retry_count,
                    error_class,
                    error_msg,
                    _iso_now(),
                    _iso_now(),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def track_extraction(extract_type: str) -> Callable:
    """装饰器：为单个提取函数自动记录 parse_jobs 状态。"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(paper_id: int, llm_client: Any, *, force: bool = False, parent_job_id: Optional[int] = None, **kwargs) -> Any:
            record_extraction_start(paper_id, extract_type, parent_job_id=parent_job_id)
            try:
                result = func(paper_id, llm_client, force=force, **kwargs)
                record_extraction_status(paper_id, extract_type, "done")
                return result
            except Exception as e:
                record_extraction_status(
                    paper_id, extract_type, "failed",
                    error_msg=str(e)[:500],
                    error_class=e.__class__.__name__,
                )
                raise
        return wrapper
    return decorator


def get_latest_extraction_status(paper_id: int, extract_type: str) -> Optional[Dict]:
    """查询某篇论文某类提取的最新状态。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, status, retry_count, error_msg, error_class, finished_at
               FROM parse_jobs
               WHERE paper_id = ? AND stage = 'extract' AND parser_used = ?
               ORDER BY id DESC
               LIMIT 1""",
            (paper_id, extract_type),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_failed_extraction_types(paper_id: int) -> List[str]:
    """返回该论文最新状态为 failed 的提取类型。"""
    failed = []
    for et in EXTRACTION_TYPES:
        status = get_latest_extraction_status(paper_id, et)
        if status and status.get("status") == "failed":
            failed.append(et)
    return failed


def reset_stale_running_jobs(stale_seconds: float = 300) -> int:
    """将长时间未完成的 running extract 任务标记为 failed，避免 killed 任务阻塞重试。

    Returns:
        重置的记录数。
    """
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(seconds=stale_seconds)).isoformat()
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE parse_jobs
               SET status = 'failed', error_class = 'StaleJob',
                   error_msg = '任务被中断或进程重启，标记为失败以便重试',
                   finished_at = ?
               WHERE stage = 'extract' AND status = 'running' AND started_at < ?""",
            (_iso_now(), cutoff),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def get_papers_needing_extraction(limit: Optional[int] = None) -> List[int]:
    """返回需要第三阶段提取的论文 ID。

    条件：
    1. 已有 fulltext；
    2. 没有任何 extract 记录，或存在 failed / stale running 记录。
    3. data_points 在没有 results/表格内容时会被标记为 skipped，视为无需重试。
    """
    # 先清理被中断的 running 任务
    reset_stale_running_jobs()

    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        # 最新状态子查询
        cur.execute("""
            SELECT paper_id, parser_used, MAX(id) AS latest_id
            FROM parse_jobs
            WHERE stage = 'extract'
            GROUP BY paper_id, parser_used
        """)
        latest_rows = cur.fetchall()

        latest_status: Dict[tuple, str] = {}
        for r in latest_rows:
            latest_status[(r["paper_id"], r["parser_used"])] = r["latest_id"]

        # 获取这些最新状态的具体值
        if latest_status:
            placeholders = ",".join(["(?,?,?)"] * len(latest_status))
            params = []
            for (pid, et), lid in latest_status.items():
                params.extend([pid, et, lid])
            cur.execute(f"""
                SELECT paper_id, parser_used, status
                FROM parse_jobs
                WHERE stage = 'extract' AND (paper_id, parser_used, id) IN ({placeholders})
            """, params)
            for r in cur.fetchall():
                latest_status[(r["paper_id"], r["parser_used"])] = r["status"]

        # 获取所有有 fulltext 的论文
        cur.execute("SELECT DISTINCT paper_id FROM paper_fulltext ORDER BY paper_id")
        all_paper_ids = [r["paper_id"] for r in cur.fetchall()]

        needing = []
        for pid in all_paper_ids:
            for et in EXTRACTION_TYPES:
                status = latest_status.get((pid, et))
                if status is None or status == "failed":
                    needing.append(pid)
                    break

        if limit:
            needing = needing[:limit]
        return needing
    finally:
        conn.close()
