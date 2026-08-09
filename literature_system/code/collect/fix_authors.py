"""
作者数据补全脚本
用途：对数据库中缺失作者的记录，通过单个 DOI 查询获取完整作者信息

使用方法:
    python fix_authors.py                              # 补全所有缺失作者的记录
    python fix_authors.py --limit 100                  # 仅补全前100条
    python fix_authors.py --db phase1_test.db          # 指定数据库
    python fix_authors.py --source crossref            # 仅补全指定来源
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path

import requests

from config import (
    CROSSREF_API_URL,
    CROSSREF_MAILTO,
    CROSSREF_USER_AGENT,
    DB_TYPE,
    DB_CONFIG,
    SQLITE_PATH,
    POLITE_REQUESTING,
)
from logger import get_logger
from db import get_connection

LOGGER = get_logger("fix_authors")


def build_headers():
    return {"User-Agent": CROSSREF_USER_AGENT}


def request_with_retry(session, url, params, max_retries=5, backoff=2):
    """带重试的请求"""
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, params=params, timeout=30)

            # 动态调整请求间隔
            if POLITE_REQUESTING:
                limit = resp.headers.get("X-Rate-Limit-Limit")
                interval = resp.headers.get("X-Rate-Limit-Interval")
                if limit and interval:
                    try:
                        interval_sec = int("".join(filter(str.isdigit, interval)))
                        sleep_time = interval_sec / int(limit)
                    except (ValueError, ZeroDivisionError):
                        sleep_time = 1
                else:
                    sleep_time = 1
            else:
                sleep_time = 1

            if resp.status_code in (429, 500, 502, 503, 504):
                LOGGER.warning("请求失败(%s)，重试 %s/%s", resp.status_code, attempt, max_retries)
                time.sleep(backoff * attempt)
                continue
            resp.raise_for_status()
            return resp.json(), sleep_time
        except requests.RequestException as exc:
            LOGGER.warning("请求异常: %s，重试 %s/%s", exc, attempt, max_retries)
            time.sleep(backoff * attempt)
    raise RuntimeError("请求失败，已超过最大重试次数")


def fetch_authors_from_crossref(doi: str, session):
    """从 Crossref 获取单个 DOI 的作者信息"""
    params = {"mailto": CROSSREF_MAILTO} if CROSSREF_MAILTO else {}
    url = f"{CROSSREF_API_URL}/{doi}"
    try:
        data, _ = request_with_retry(session, url, params)
        item = data.get("message", {})
        authors = item.get("author", [])
        return _format_authors(authors)
    except Exception as e:
        LOGGER.error("获取 DOI %s 作者失败: %s", doi, e)
        return None


def _format_authors(author_list):
    """格式化作者列表为 JSON 字符串"""
    if not author_list:
        return None
    result = []
    for a in author_list:
        given = a.get("given", "")
        family = a.get("family", "")
        if given and family:
            result.append(f"{given} {family}")
        elif family:
            result.append(family)
    return ", ".join(result) if result else None


def find_records_without_authors(conn, source=None, limit=None):
    """查找缺失作者的记录"""
    sql = """
        SELECT doi, id FROM papers 
        WHERE (author IS NULL OR author = '' OR author = '[]')
    """
    params = []
    if source:
        sql += " AND source = ?"
        params.append(source)
    if limit:
        sql += f" LIMIT {limit}"
    
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def update_author(conn, paper_id, author_str):
    """更新作者的作者信息"""
    cur = conn.cursor()
    cur.execute("UPDATE papers SET author = ? WHERE id = ?", (author_str, paper_id))
    conn.commit()
    return cur.rowcount > 0


def fix_authors(db_path: Path, source=None, limit=None, dry_run=False):
    """
    补全缺失的作者信息
    
    Args:
        db_path: 数据库路径
        source: 仅处理指定来源（如 'crossref'）
        limit: 最大处理条数
        dry_run: 仅模拟，不实际更新
    """
    conn = get_connection(db_path=db_path)
    session = requests.Session()
    session.headers.update(build_headers())

    try:
        records = find_records_without_authors(conn, source, limit)
        total = len(records)
        
        if total == 0:
            LOGGER.info("没有发现缺失作者的记录")
            return {"total": 0, "fixed": 0, "failed": 0}

        LOGGER.info("发现 %d 条记录缺失作者信息", total)
        
        fixed = 0
        failed = 0
        skipped = 0

        for i, (doi, paper_id) in enumerate(records):
            LOGGER.info("[%d/%d] 正在获取 DOI: %s", i + 1, total, doi)
            
            if dry_run:
                LOGGER.info("  [DRY RUN] 将会补全 author 字段")
                fixed += 1
                continue

            # 获取作者信息
            authors = fetch_authors_from_crossref(doi, session)
            
            if authors:
                success = update_author(conn, paper_id, authors)
                if success:
                    LOGGER.info("  ✓ 成功补全: %s", authors[:80] + "..." if len(authors) > 80 else authors)
                    fixed += 1
                else:
                    LOGGER.warning("  ✗ 更新失败")
                    failed += 1
            else:
                LOGGER.warning("  ✗ 未获取到作者信息")
                failed += 1

            # 遵循礼貌请求策略
            time.sleep(1)

        LOGGER.info("--- 作者补全报告 ---")
        LOGGER.info("总记录数: %d", total)
        LOGGER.info("成功补全: %d", fixed)
        LOGGER.info("失败: %d", failed)
        LOGGER.info("--------------------")

        return {"total": total, "fixed": fixed, "failed": failed}

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="作者数据补全脚本")
    parser.add_argument("--db", default=str(SQLITE_PATH), help="数据库路径")
    parser.add_argument("--source", default=None, help="仅处理指定来源 (如: crossref)")
    parser.add_argument("--limit", type=int, default=None, help="最大处理条数")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不实际更新")
    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db)
    
    if not db_path.exists():
        LOGGER.error("数据库文件不存在: %s", db_path)
        return

    LOGGER.info("数据库: %s", db_path)
    if args.dry_run:
        LOGGER.info("模式: DRY RUN（仅模拟）")
    
    fix_authors(db_path, args.source, args.limit, args.dry_run)


if __name__ == "__main__":
    main()
