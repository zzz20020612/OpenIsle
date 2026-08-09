"""
多源数据采集与作者补全脚本
整合 Crossref、Semantic Scholar，自动处理作者缺失问题

采集策略:
1. 优先使用 Crossref 列表查询（已添加 select 参数强制返回 author）
2. 入库后检测缺失作者的记录
3. 对缺失作者使用 Crossref 单 DOI 查询补全
4. Crossref 仍缺失时，使用 Semantic Scholar 兜底

使用方法:
    python multi_source_collector.py --keyword livestock --rows 100
    python multi_source_collector.py --keyword livestock --fix-only  # 仅补全现有数据
"""
import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import (
    CHECKPOINT_DIR,
    CROSSREF_API_URL,
    CROSSREF_MAILTO,
    CROSSREF_USER_AGENT,
    DB_TYPE,
    DB_CONFIG,
    KEYWORD,
    MAX_PAGES,
    ROWS_PER_PAGE,
    SLEEP_BETWEEN,
    SQLITE_PATH,
    POLITE_REQUESTING,
    RAW_JSON_DIR,
    ARTICLE_TYPES_FILTER,
)
from logger import get_logger
from sources.semantic_scholar import SemanticScholarAdapter
from utils import normalize_crossref_item, parse_authors
from db import get_connection

LOGGER = get_logger("multi_collector")

# ============ Crossref 采集相关 ============

def build_headers():
    return {"User-Agent": CROSSREF_USER_AGENT}


def request_with_retry(session, url, params, max_retries=5, backoff=2):
    calculated_sleep = SLEEP_BETWEEN
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
            if POLITE_REQUESTING:
                limit = resp.headers.get("X-Rate-Limit-Limit")
                interval = resp.headers.get("X-Rate-Limit-Interval")
                if limit and interval:
                    try:
                        interval_sec = int("".join(filter(str.isdigit, interval)))
                        calculated_sleep = interval_sec / int(limit)
                    except (ValueError, ZeroDivisionError):
                        pass
            if resp.status_code in (429, 500, 502, 503, 504):
                LOGGER.warning("请求失败(%s)，重试 %s/%s", resp.status_code, attempt, max_retries)
                time.sleep(backoff * attempt)
                continue
            resp.raise_for_status()
            return resp, calculated_sleep
        except requests.RequestException as exc:
            LOGGER.warning("请求异常: %s，重试 %s/%s", exc, attempt, max_retries)
            time.sleep(backoff * attempt)
    raise RuntimeError("请求失败，已超过最大重试次数")


def fetch_crossref_page(session, keyword, offset, rows, start_date=None, end_date=None):
    """获取单页 Crossref 数据"""
    params = {
        "query": keyword,
        "rows": rows,
        "offset": offset,
    }
    # 注意：Crossref 列表查询不支持 select 返回 author
    # author 必须通过单 DOI 查询获取（见 fix_authors_with_crossref 函数）
    if start_date:
        params["filter"] = f"from-pub-date:{start_date}"
    if end_date:
        params["filter"] = (params.get("filter", "") + f",until-pub-date:{end_date}").lstrip(",")
    article_types = [value.strip() for value in ARTICLE_TYPES_FILTER.split(",") if value.strip()]
    if article_types:
        # Crossref accepts one work type per query. Filtering here prevents
        # peer-review records and components from entering the PDF workflow.
        params["filter"] = (params.get("filter", "") + f",type:{article_types[0]}").lstrip(",")
    if CROSSREF_MAILTO:
        params["mailto"] = CROSSREF_MAILTO

    resp, sleep_time = request_with_retry(session, CROSSREF_API_URL, params)
    data = resp.json()
    return data.get("message", {}).get("items", []), sleep_time


def fetch_crossref_batch(keyword, rows, max_pages, start_date=None, end_date=None):
    """批量获取 Crossref 数据"""
    session = requests.Session()
    session.headers.update(build_headers())
    
    all_items = []
    for page in range(max_pages):
        offset = page * rows
        LOGGER.info("获取 Crossref 第 %d 页 (offset=%d)", page + 1, offset)
        items, sleep_time = fetch_crossref_page(session, keyword, offset, rows, start_date, end_date)
        if not items:
            LOGGER.info("无更多数据")
            break
        all_items.extend(items)
        LOGGER.info("累计获取 %d 条", len(all_items))
        time.sleep(sleep_time)
    
    return all_items


def fetch_single_doi(doi):
    """通过 DOI 获取单条元数据（用于补全）"""
    session = requests.Session()
    session.headers.update(build_headers())
    params = {"mailto": CROSSREF_MAILTO} if CROSSREF_MAILTO else {}
    url = f"{CROSSREF_API_URL}/{doi}"
    try:
        resp, _ = request_with_retry(session, url, params)
        return resp.json().get("message")
    except Exception as e:
        LOGGER.error("获取 DOI %s 失败: %s", doi, e)
        return None


# ============ 数据库相关 ============

def is_sqlite():
    return DB_TYPE == "sqlite"


def placeholder():
    return "?" if is_sqlite() else "%s"


def upsert_paper(conn, item, source="crossref"):
    """入库单条记录"""
    doi = item.get("DOI") or item.get("doi")
    if not doi:
        return None

    title = item.get("title")
    if isinstance(title, list):
        title = " ".join(title).strip() or None

    # 处理 author 字段 - 确保转换为字符串格式
    author_data = item.get("author", [])
    if isinstance(author_data, str):
        authors = author_data
    elif isinstance(author_data, list):
        # 格式化为 "Given Family, Given Family, ..." 格式
        authors_list = []
        for a in author_data:
            given = a.get("given", "")
            family = a.get("family", "")
            if given and family:
                authors_list.append(f"{given} {family}")
            elif family:
                authors_list.append(family)
        authors = ", ".join(authors_list) if authors_list else ""
    else:
        authors = str(author_data) if author_data else ""

    publisher = item.get("publisher", "")
    published_date = item.get("published_date") or item.get("date")
    abstract = item.get("abstract", "")
    journal = item.get("journal") or item.get("container-title", [])
    if isinstance(journal, list):
        journal = journal[0] if journal else ""
    article_type = item.get("type") or item.get("article_type", "")
    oa_url = item.get("oa_url", "")
    oa_category = item.get("oa_category", "")
    meta_json = json.dumps(item, ensure_ascii=False)

    cur = conn.cursor()
    sql = f"""
        INSERT INTO papers (doi, source, title, author, publisher, published_date, abstract, journal, article_type, oa_url, oa_category, meta_json)
        VALUES ({placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()}, {placeholder()})
        ON CONFLICT(doi) DO UPDATE SET
            author=excluded.author,
            oa_url=excluded.oa_url,
            oa_category=excluded.oa_category,
            meta_json=excluded.meta_json;
    """
    try:
        cur.execute(sql, (doi, source, title, authors, publisher, published_date, abstract, journal, article_type, oa_url, oa_category, meta_json))
        conn.commit()
        cur.execute("SELECT id FROM papers WHERE doi = ?", (doi,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        LOGGER.error("入库失败 %s: %s", doi, e)
        conn.rollback()
        return None


def find_missing_authors(conn):
    """查找缺失作者的记录"""
    cur = conn.cursor()
    cur.execute("SELECT doi, id FROM papers WHERE author IS NULL OR author = '' OR author = '[]'")
    return cur.fetchall()


def update_author(conn, paper_id, authors):
    """更新作者字段"""
    cur = conn.cursor()
    cur.execute("UPDATE papers SET author = ? WHERE id = ?", (authors, paper_id))
    conn.commit()
    return cur.rowcount > 0


# ============ 作者补全主流程 ============

def fix_authors_with_crossref(conn, limit=None):
    """使用 Crossref 补全缺失的作者"""
    records = find_missing_authors(conn)
    if not records:
        LOGGER.info("没有缺失作者的记录")
        return {"total": 0, "fixed": 0, "failed": 0}
    
    total = len(records)
    if limit:
        records = records[:limit]
    
    LOGGER.info("发现 %d 条记录缺失作者，使用 Crossref 单 DOI 查询补全", total)
    
    fixed = 0
    failed = 0
    
    for i, (doi, paper_id) in enumerate(records):
        LOGGER.info("[%d/%d] 查询 DOI: %s", i + 1, total, doi)
        
        item = fetch_single_doi(doi)
        if item:
            authors_data = item.get("author", [])
            if authors_data:
                authors_str = ", ".join([
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in authors_data if a.get('family')
                ])
                if authors_str and update_author(conn, paper_id, authors_str):
                    LOGGER.info("  ✓ 补全成功: %s", authors_str[:60] + "..." if len(authors_str) > 60 else authors_str)
                    fixed += 1
                else:
                    LOGGER.warning("  ✗ 格式化作者失败")
                    failed += 1
            else:
                LOGGER.warning("  ✗ Crossref 无作者数据")
                failed += 1
        else:
            LOGGER.warning("  ✗ 无法获取 DOI 数据")
            failed += 1
        
        time.sleep(1)  # 礼貌请求

    return {"total": total, "fixed": fixed, "failed": failed}


def fix_authors_with_semantic_scholar(conn, limit=None, batch_size: int = 100):
    """使用 Semantic Scholar 批量补全缺失的作者。

    优先调用 /paper/batch 端点一次性查询多个 DOI，减少网络往返。
    对批量未命中的记录，再通过标题搜索兜底。
    """
    records = find_missing_authors(conn)
    if not records:
        LOGGER.info("没有缺失作者的记录")
        return {"total": 0, "fixed": 0, "failed": 0, "skipped": 0}

    total = len(records)
    if limit:
        records = records[:limit]

    LOGGER.info("发现 %d 条记录缺失作者，使用 Semantic Scholar 批量补全", total)

    adapter = SemanticScholarAdapter()
    fixed = 0
    failed = 0
    skipped = 0

    # 1) 批量 DOI 查询
    doi_to_paper_id = {doi.lower(): paper_id for doi, paper_id in records if doi}
    if doi_to_paper_id:
        LOGGER.info("批量查询 %d 个 DOI...", len(doi_to_paper_id))
        try:
            batch_results = adapter.fetch_by_dois_batch(
                list(doi_to_paper_id.keys()), batch_size=batch_size
            )
            for doi_key, result in batch_results.items():
                paper_id = doi_to_paper_id.get(doi_key)
                if not paper_id:
                    continue
                authors_str = result.get("author", "")
                if authors_str and update_author(conn, paper_id, authors_str):
                    LOGGER.info("  ✓ Semantic Scholar 批量补全成功 paper_id=%d: %s", paper_id, authors_str[:50] + "..." if len(authors_str) > 50 else authors_str)
                    fixed += 1
                else:
                    skipped += 1
        except Exception as e:
            LOGGER.error("Semantic Scholar 批量查询失败: %s", e)
            failed += len(doi_to_paper_id)

    # 2) 对仍缺失作者的记录，通过标题搜索兜底
    remaining = find_missing_authors(conn)
    if remaining:
        LOGGER.info("批量查询后仍有 %d 条缺失作者，使用标题搜索兜底", len(remaining))
        for i, (doi, paper_id) in enumerate(remaining):
            LOGGER.info("[%d/%d] 标题搜索 DOI: %s", i + 1, len(remaining), doi)
            try:
                cur = conn.cursor()
                cur.execute("SELECT title FROM papers WHERE id = ?", (paper_id,))
                row = cur.fetchone()
                result = None
                if row and row[0]:
                    search_results = adapter.fetch(row[0], page=0, page_size=1)
                    if search_results:
                        result = search_results[0]

                if result and result.get("author"):
                    authors_str = result.get("author", "")
                    if authors_str and update_author(conn, paper_id, authors_str):
                        LOGGER.info("  ✓ Semantic Scholar 标题搜索补全成功: %s", authors_str[:50] + "..." if len(authors_str) > 50 else authors_str)
                        fixed += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            except Exception as e:
                LOGGER.error("  ✗ 标题搜索失败: %s", e)
                failed += 1
            time.sleep(0.5)  # 避免限流

    return {"total": total, "fixed": fixed, "failed": failed, "skipped": skipped}


def fix_authors_multi_strategy(conn, limit=None):
    """多策略补全作者（先 Crossref，再 Semantic Scholar）"""
    LOGGER.info("=== 开始多策略作者补全 ===")
    
    # 步骤 1: Crossref 单 DOI 查询
    LOGGER.info("\n--- 步骤 1: Crossref 单 DOI 查询 ---")
    result1 = fix_authors_with_crossref(conn, limit)
    LOGGER.info("Crossref 补全结果: %s", result1)
    
    # 检查剩余缺失
    remaining = find_missing_authors(conn)
    if remaining:
        LOGGER.info("\n--- 步骤 2: Semantic Scholar 兜底 ---")
        result2 = fix_authors_with_semantic_scholar(conn)
        LOGGER.info("Semantic Scholar 补全结果: %s", result2)
        return {"crossref": result1, "semantic_scholar": result2}
    
    return {"crossref": result1, "semantic_scholar": {"total": 0, "fixed": 0, "failed": 0, "skipped": 0}}


# ============ 主采集流程 ============

def _filter_new_items(conn, items):
    """过滤掉数据库中已存在 DOI 的条目，返回新条目和重复数量。"""
    if not items:
        return [], 0

    # 提取有效 DOI
    doiset = set()
    doi_to_item = {}
    for item in items:
        doi = item.get("DOI") or item.get("doi")
        if not doi:
            continue
        doi = doi.lower().strip()
        doiset.add(doi)
        doi_to_item[doi] = item

    if not doiset:
        return [], 0

    cur = conn.cursor()
    placeholders = ",".join([placeholder()] * len(doiset))
    cur.execute(f"SELECT LOWER(doi) AS doi FROM papers WHERE doi IN ({placeholders})", tuple(doiset))
    existing = {r[0] for r in cur.fetchall()}

    new_items = [doi_to_item[d] for d in doiset if d not in existing]
    duplicate_count = len(doiset) - len(new_items)
    return new_items, duplicate_count


def run_collection(keyword, rows, max_pages, start_date, end_date, db_path, fix_authors_flag=True):
    """完整采集流程（支持逐页去重与无新增时提前终止）"""
    LOGGER.info("=== 开始采集 ===")
    LOGGER.info("关键词: %s", keyword)
    LOGGER.info("目标数量: %d 条", rows)

    from pathlib import Path
    conn = get_connection(db_path=Path(db_path) if db_path else None)

    # 步骤 1: Crossref 逐页采集，每页查库去重，整页重复则提前终止
    LOGGER.info("\n--- 步骤 1: Crossref 批量采集 ---")
    session = requests.Session()
    session.headers.update(build_headers())

    all_items = []
    inserted = 0
    total_fetched = 0
    empty_page_count = 0

    for page in range(max_pages):
        offset = page * rows
        LOGGER.info("获取 Crossref 第 %d 页 (offset=%d)", page + 1, offset)
        try:
            items, sleep_time = fetch_crossref_page(session, keyword, offset, rows, start_date, end_date)
        except Exception as exc:
            LOGGER.error("获取第 %d 页失败: %s", page + 1, exc)
            break

        if not items:
            LOGGER.info("无更多数据")
            break

        total_fetched += len(items)
        new_items, duplicate_count = _filter_new_items(conn, items)
        LOGGER.info("本页 %d 条，其中重复 %d 条，新增 %d 条", len(items), duplicate_count, len(new_items))

        if not new_items:
            empty_page_count += 1
            # 连续两页都无新增，认为已采集完，提前终止
            if empty_page_count >= 2:
                LOGGER.info("连续 %d 页无新增 DOI，终止采集以节省 API 调用", empty_page_count)
                break
            time.sleep(sleep_time)
            continue

        empty_page_count = 0
        all_items.extend(new_items)

        # 步骤 2: 数据入库（仅新条目）
        for item in new_items:
            normalized = normalize_crossref_item(item)
            paper_id = upsert_paper(conn, normalized, source="crossref")
            if paper_id:
                inserted += 1

        LOGGER.info("累计入库 %d 条", inserted)
        time.sleep(sleep_time)

        if inserted >= rows:
            LOGGER.info("已达到目标数量 %d，提前终止", rows)
            break

    LOGGER.info("Crossref 获取 %d 条原始数据，入库 %d 条", total_fetched, inserted)

    # 步骤 3: 作者补全
    if fix_authors_flag and inserted > 0:
        LOGGER.info("\n--- 步骤 3: 作者补全 ---")
        result = fix_authors_multi_strategy(conn)

        # 最终统计
        remaining = find_missing_authors(conn)
        LOGGER.info("\n=== 最终作者完整率 ===")
        LOGGER.info("入库总数: %d", inserted)
        LOGGER.info("仍缺失作者: %d", len(remaining))
        LOGGER.info("作者完整率: %.1f%%", (inserted - len(remaining)) / inserted * 100 if inserted > 0 else 0)

    session.close()
    conn.close()
    return inserted


def parse_args():
    parser = argparse.ArgumentParser(description="多源数据采集与作者补全")
    parser.add_argument("--keyword", default=KEYWORD, help="采集关键词")
    parser.add_argument("--rows", type=int, default=ROWS_PER_PAGE, help="每页条数")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES, help="最大页数")
    parser.add_argument("--start-date", default=None, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--db", default=str(SQLITE_PATH), help="数据库路径")
    parser.add_argument("--fix-only", action="store_true", help="仅执行作者补全，不采集新数据")
    parser.add_argument("--no-fix", action="store_true", help="采集后不执行作者补全")
    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db)
    
    if args.fix_only:
        LOGGER.info("=== 仅执行作者补全 ===")
        conn = get_connection(db_path=db_path)
        result = fix_authors_multi_strategy(conn)
        LOGGER.info("补全结果: %s", result)
        conn.close()
    else:
        run_collection(
            args.keyword,
            args.rows,
            args.max_pages,
            args.start_date,
            args.end_date,
            db_path,
            fix_authors_flag=not args.no_fix
        )


if __name__ == "__main__":
    main()
