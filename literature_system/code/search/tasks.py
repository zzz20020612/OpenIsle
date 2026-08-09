"""异步任务与进度追踪。

为耗时操作（重建索引、同步论文等）提供内存任务队列，
前端可通过 /progress/<task_id> 轮询进度。
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from logger import get_logger

LOGGER = get_logger("search.tasks")

# 内存任务队列；当前数据量小，内存足够
_tasks: Dict[str, Dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="search_task_")


def cleanup_tasks(max_age: float = 3600) -> int:
    """清理已完成/失败超过 max_age 秒的任务，防止内存无限增长。"""
    now = time.time()
    to_remove = [
        tid for tid, task in _tasks.items()
        if task.get("status") in ("done", "failed")
        and now - task.get("updated_at", now) > max_age
    ]
    for tid in to_remove:
        del _tasks[tid]
    return len(to_remove)


def submit_task(fn: Callable, *args, **kwargs) -> str:
    """提交一个异步任务，返回 task_id。"""
    cleanup_tasks()
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "message": "等待执行...",
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    def _wrapper():
        try:
            _update(task_id, status="running", progress=0.0, message="开始执行")
            # 将任务对象传给 fn，便于内部报告进度
            result = fn(_TaskProxy(task_id), *args, **kwargs)
            _update(task_id, status="done", progress=100.0, message="完成", result=result)
        except Exception as exc:
            LOGGER.exception("异步任务失败: task_id=%s", task_id)
            _update(task_id, status="failed", message=f"失败: {exc}", error=str(exc))

    _executor.submit(_wrapper)
    return task_id


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """查询任务状态。"""
    task = _tasks.get(task_id)
    if not task:
        return None
    return dict(task)


def _update(task_id: str, **kwargs) -> None:
    task = _tasks.get(task_id)
    if not task:
        return
    task.update(kwargs)
    task["updated_at"] = time.time()


class _TaskProxy:
    """任务进度代理对象，传给具体任务函数以报告进度。"""

    def __init__(self, task_id: str):
        self.task_id = task_id

    def set_progress(self, progress: float, message: str = "") -> None:
        progress = max(0.0, min(100.0, float(progress)))
        update = {"progress": progress}
        if message:
            update["message"] = message
        _update(self.task_id, **update)
