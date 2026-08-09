"""
解析任务调度器（状态机 + 失败分类 + 重试/降级）

阶段：download → parse → extract
状态：pending → running → done / failed / permanent_failed
解析器优先级链：MinerU API → PyMuPDF → Marker GPU（可配置）

依赖：
    - config.py 中的 PDF_PARSER_STRATEGY / MINERU_* 配置
    - 数据库表 parse_jobs / paper_fulltext / paper_sections / paper_figures
"""
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

import sys
from pathlib import Path
_CODE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CODE_ROOT.parent
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config
from logger import get_logger
from db import get_conn

log = get_logger("parse_scheduler")


# ============================================================
# parse_jobs 状态机
# ============================================================
def create_job(paper_id: int, stage: str = "parse", parent_job_id: Optional[int] = None) -> int:
    """创建一个解析任务，返回 job_id。若已有未完成同 stage 任务则复用。"""
    conn = get_conn()
    cur = conn.cursor()
    # 检查是否已有同 paper + stage 的未完成任务
    cur.execute(
        "SELECT id, status FROM parse_jobs WHERE paper_id=? AND stage=? ORDER BY id DESC LIMIT 1",
        (paper_id, stage),
    )
    row = cur.fetchone()
    if row and row["status"] in ("pending", "running"):
        conn.close()
        return row["id"]
    cur.execute(
        """INSERT INTO parse_jobs
           (paper_id, stage, status, retry_count, max_retries, parent_job_id, started_at)
           VALUES (?, ?, 'pending', 0, 3, ?, ?)""",
        (paper_id, stage, parent_job_id, datetime.now().isoformat()),
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    log.info(f"created job #{job_id} for paper_id={paper_id} stage={stage} parent={parent_job_id}")
    return job_id


def update_job(
    job_id: int,
    status: Optional[str] = None,
    parser_used: Optional[str] = None,
    error_class: Optional[str] = None,
    error_msg: Optional[str] = None,
    mineru_task_id: Optional[str] = None,
    retry_count: Optional[int] = None,
):
    """更新任务状态。仅传需要更新的字段。"""
    conn = get_conn()
    cur = conn.cursor()
    sets, args = [], []
    if status:
        sets.append("status = ?")
        args.append(status)
        if status in ("done", "failed", "permanent_failed"):
            sets.append("finished_at = ?")
            args.append(datetime.now().isoformat())
    if parser_used:
        sets.append("parser_used = ?")
        args.append(parser_used)
    if error_class:
        sets.append("error_class = ?")
        args.append(error_class)
    if error_msg:
        sets.append("error_msg = ?")
        args.append(error_msg)
    if mineru_task_id:
        sets.append("mineru_task_id = ?")
        args.append(mineru_task_id)
    if retry_count is not None:
        sets.append("retry_count = ?")
        args.append(retry_count)
    if not sets:
        conn.close()
        return
    args.append(job_id)
    cur.execute(f"UPDATE parse_jobs SET {', '.join(sets)} WHERE id = ?", args)
    conn.commit()
    conn.close()


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM parse_jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# 失败分类与降级策略
# ============================================================
# 错误类别 → 是否重试 / 降级到哪个解析器
ERROR_POLICY = {
    # 下载类
    "network_timeout":      {"retry": True,  "max_retries": 3, "fallback": None},
    "http_403":             {"retry": False, "max_retries": 0, "fallback": None},
    "http_404":             {"retry": False, "max_retries": 0, "fallback": None},
    "http_429":             {"retry": True,  "max_retries": 1, "fallback": None},
    "not_pdf":              {"retry": False, "max_retries": 0, "fallback": None},
    "corrupted_pdf":        {"retry": False, "max_retries": 0, "fallback": None},
    "encrypted_pdf":        {"retry": False, "max_retries": 0, "fallback": None},
    # MinerU 类
    "mineru_upload_failed":     {"retry": True,  "max_retries": 3, "fallback": "pymupdf"},
    "mineru_task_timeout":      {"retry": True,  "max_retries": 1, "fallback": "marker_gpu"},
    "mineru_quota_exceeded":    {"retry": False, "max_retries": 0, "fallback": "pymupdf"},
    # Marker 类
    "marker_oom":           {"retry": False, "max_retries": 0, "fallback": "pymupdf"},
    # 提取类
    "no_section_detected":  {"retry": False, "max_retries": 0, "fallback": None},
}


def classify_error(err: Exception, context: str = "") -> str:
    """根据异常文本判断错误类别。"""
    explicit_class = getattr(err, "error_class", None)
    if explicit_class:
        return explicit_class
    msg = str(err).lower()
    if "timeout" in msg or "timed out" in msg:
        if "mineru" in context:
            return "mineru_task_timeout"
        return "network_timeout"
    if "403" in msg or "forbidden" in msg:
        return "http_403"
    if "404" in msg or "not found" in msg:
        return "http_404"
    if "429" in msg or "too many requests" in msg:
        return "http_429"
    if "not a pdf" in msg or "not_pdf" in msg or b"%pdf" not in (getattr(err, "content", b"") or b""):
        # 仅在明显场景标记
        if "not a pdf" in msg or "content-type" in msg:
            return "not_pdf"
    if "encrypted" in msg:
        return "encrypted_pdf"
    if "is not a document" in msg or "damaged" in msg or "corrupt" in msg:
        return "corrupted_pdf"
    if "out of memory" in msg or "cuda oom" in msg:
        return "marker_oom"
    return "network_timeout"  # 默认归为网络类


# ============================================================
# 解析器优先级链
# ============================================================
def get_parser_chain() -> List[str]:
    """根据 config.PDF_PARSER_STRATEGY 返回有序解析器列表（priority>0，按升序）。"""
    strategy = config.PDF_PARSER_STRATEGY
    chain = sorted(
        [name for name, p in strategy.items() if p > 0],
        key=lambda n: strategy[n],
    )
    return chain


def get_next_fallback(current_parser: str, error_class: str) -> Optional[str]:
    """根据当前解析器与错误类别，返回下一个降级解析器。"""
    policy = ERROR_POLICY.get(error_class)
    if not policy or not policy.get("fallback"):
        return None
    fallback = policy["fallback"]
    chain = get_parser_chain()
    # 找当前解析器之后、且为 fallback 的解析器
    try:
        idx = chain.index(current_parser)
    except ValueError:
        return fallback if fallback in chain else None
    for name in chain[idx + 1:]:
        if name == fallback:
            return name
    return None


# ============================================================
# MinerU 配额管理
# ============================================================
def get_mineru_usage_today() -> int:
    """返回今日 MinerU 已使用次数。"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT COUNT(*) as cnt FROM parse_jobs
           WHERE parser_used = 'mineru_api'
             AND DATE(started_at) = DATE('now')""",
    )
    row = cur.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def mineru_quota_exceeded() -> bool:
    return get_mineru_usage_today() >= config.MINERU_DAILY_QUOTA


# ============================================================
# 主入口：处理单篇论文
# ============================================================
def process_paper(paper_id: int, force: bool = False, parent_job_id: Optional[int] = None) -> Dict[str, Any]:
    """
    处理单篇论文的完整 parse pipeline。

    Args:
        paper_id: papers.id
        force: 是否强制重新解析（忽略已有 done 任务）
        parent_job_id: 触发本次处理的上级 job id（重试/降级链路）

    Returns:
        {
            "paper_id": int,
            "status": "done" | "failed" | "skipped",
            "parser_used": str | None,
            "error_class": str | None,
            "error_msg": str | None,
        }
    """
    # 延迟导入避免循环依赖
    from pdf.pipeline import PdfPipeline

    # 检查是否已有 done 任务或已生成 section
    if not force:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM parse_jobs WHERE paper_id=? AND stage='parse' AND status='done' LIMIT 1",
            (paper_id,),
        )
        has_done_job = cur.fetchone()
        cur.execute("SELECT 1 FROM paper_sections WHERE paper_id=? LIMIT 1", (paper_id,))
        has_section = cur.fetchone()
        cur.execute("SELECT 1 FROM paper_fulltext WHERE paper_id=?", (paper_id,))
        has_fulltext = cur.fetchone()
        conn.close()
        if has_done_job or has_section or has_fulltext:
            log.info(f"paper_id={paper_id} 已有解析记录，跳过")
            return {"paper_id": paper_id, "status": "skipped", "parser_used": None,
                    "error_class": None, "error_msg": None}

    # 创建任务（重试/降级时记录来源 job）
    job_id = create_job(paper_id, stage="parse", parent_job_id=parent_job_id)
    update_job(job_id, status="running")

    pipeline = PdfPipeline()
    try:
        result = pipeline.run(paper_id, job_id)
        update_job(job_id, status="done", parser_used=result.get("parser_used"))

        # 解析成功后立即抽取并归一化作者/机构信息
        try:
            from scripts.populate_authors import populate_for_paper
            populate_for_paper(paper_id)
        except Exception as author_err:
            log.warning(f"paper_id={paper_id} 作者信息填充失败（不影响解析主流程）: {author_err}")

        return {
            "paper_id": paper_id,
            "status": "done",
            "parser_used": result.get("parser_used"),
            "error_class": None,
            "error_msg": None,
        }
    except Exception as e:
        error_class = classify_error(e, context=getattr(e, "context", ""))
        policy = ERROR_POLICY.get(error_class, {})
        retry = policy.get("retry", False)
        fallback = get_next_fallback(getattr(e, "parser", ""), error_class)

        log.error(f"paper_id={paper_id} 解析失败: {error_class} - {e}; retry={retry}, fallback={fallback}")

        job = get_job(job_id)
        retry_count = (job["retry_count"] or 0) + 1 if job else 1
        max_retries = policy.get("max_retries", 0)

        if retry and retry_count <= max_retries:
            # 指数退避
            wait = min(5 * (2 ** (retry_count - 1)), 300)
            log.info(f"等待 {wait}s 后重试 job #{job_id}（第 {retry_count}/{max_retries} 次）")
            time.sleep(wait)
            update_job(job_id, status="pending", retry_count=retry_count,
                       error_class=error_class, error_msg=str(e)[:500])
            return process_paper(paper_id, force=True, parent_job_id=job_id)
        elif fallback:
            log.info(f"降级到 {fallback} 处理 paper_id={paper_id}")
            update_job(job_id, status="pending", parser_used=fallback,
                       retry_count=0, error_class=error_class, error_msg=str(e)[:500])
            return process_paper(paper_id, force=True, parent_job_id=job_id)
        else:
            update_job(job_id, status="permanent_failed",
                       error_class=error_class, error_msg=str(e)[:500])
            return {
                "paper_id": paper_id,
                "status": "failed",
                "parser_used": None,
                "error_class": error_class,
                "error_msg": str(e)[:500],
            }


# ============================================================
# 批量处理
# ============================================================
def process_pending_papers(limit: int = 100, force: bool = False) -> Dict[str, int]:
    """
    批量处理数据库中所有待解析的论文。

    Args:
        limit: 最多处理数量
        force: 是否强制重新解析

    Returns:
        {"total": int, "done": int, "failed": int, "skipped": int}
    """
    conn = get_conn()
    cur = conn.cursor()

    if force:
        cur.execute("SELECT id FROM papers WHERE doi IS NOT NULL LIMIT ?", (limit,))
    else:
        # 排除已有 paper_fulltext 的
        cur.execute(
            """SELECT p.id FROM papers p
               LEFT JOIN paper_fulltext pf ON p.id = pf.paper_id
               WHERE p.doi IS NOT NULL AND pf.paper_id IS NULL
               LIMIT ?""",
            (limit,),
        )
    paper_ids = [r["id"] for r in cur.fetchall()]
    conn.close()

    stats = {"total": len(paper_ids), "done": 0, "failed": 0, "skipped": 0}
    log.info(f"待处理论文: {len(paper_ids)} 篇")

    for i, pid in enumerate(paper_ids, 1):
        log.info(f"[{i}/{len(paper_ids)}] 处理 paper_id={pid}")
        try:
            result = process_paper(pid, force=force)
            stats[result["status"]] = stats.get(result["status"], 0) + 1
        except Exception as e:
            log.error(f"paper_id={pid} 处理异常: {e}")
            stats["failed"] += 1

    log.info(f"批量处理完成: {stats}")
    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PDF 内容提取 pipeline 调度器")
    parser.add_argument("--paper-id", type=int, help="处理单个 paper_id")
    parser.add_argument("--limit", type=int, default=10, help="批量处理上限")
    parser.add_argument("--force", action="store_true", help="强制重新解析")
    args = parser.parse_args()

    if args.paper_id:
        result = process_paper(args.paper_id, force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        stats = process_pending_papers(limit=args.limit, force=args.force)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
