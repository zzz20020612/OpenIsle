"""
Crossref 主采集与入库脚本
支持：参数化、重试、断点续跑、子表入库、JSON备份与报告
"""

import sys
from pathlib import Path

# 确保能找到 code/ 目录下的模块
_CODE_ROOT = Path(__file__).resolve().parent.parent
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

import argparse
import json
import time
from datetime import datetime, timezone

import sqlite3
import requests

from config import (
    CHECKPOINT_DIR,
    CROSSREF_API_URL,
    CROSSREF_END_DATE,
    CROSSREF_MAILTO,
    CROSSREF_START_DATE,
    CROSSREF_USER_AGENT,
    DB_TYPE,
    DB_CONFIG,
    KEYWORD,
    MAX_PAGES,
    RAW_JSON_DIR,
    ROWS_PER_PAGE,
    SLEEP_BETWEEN,
    SQLITE_PATH,
    POLITE_REQUESTING,
    ARTICLE_TYPES_FILTER,
    ARTICLE_TYPE_MAPPING,
)
from logger import get_logger
from utils import (
    clean_abstract,
    parse_authors,
    parse_funders,
    parse_licenses,
    parse_links,
    parse_published_date,
    parse_relations,
    normalize_crossref_item,
    get_journal_tier,
)
from author.author_resolution import resolve_paper
from db import get_connection

LOGGER = get_logger("crossref")


def is_sqlite():
    return DB_TYPE == "sqlite"


def placeholder():
    return "?" if is_sqlite() else "%s"


def placeholders(n):
    return ", ".join([placeholder()] * n)


def build_headers():
    headers = {
        "User-Agent": CROSSREF_USER_AGENT,
    }
    return headers


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
                        # interval is like "1s", so we parse the number
                        interval_sec = int("".join(filter(str.isdigit, interval)))
                        calculated_sleep = interval_sec / int(limit)
                    except (ValueError, ZeroDivisionError):
                        pass  # Fallback to default sleep

            if resp.status_code in (429, 500, 502, 503, 504):
                LOGGER.warning("请求失败(%s)，重试 %s/%s", resp.status_code, attempt, max_retries)
                time.sleep(backoff * attempt)
                continue
            resp.raise_for_status()
            return resp, calculated_sleep
        except requests.RequestException as exc:
            LOGGER.warning("请求异常：%s，重试 %s/%s", exc, attempt, max_retries)
            time.sleep(backoff * attempt)
    raise RuntimeError("请求失败，已超过最大重试次数")


def load_checkpoint(checkpoint_path: Path):
    if checkpoint_path.exists():
        return json.loads(checkpoint_path.read_text(encoding="utf-8"))
    return None


def save_checkpoint(checkpoint_path: Path, payload: dict):
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_crossref_metadata(
    keyword, rows, max_pages, start_date, end_date, resume=False, use_cursor=False, article_types=None
):
    session = requests.Session()
    session.headers.update(build_headers())

    all_items = []
    checkpoint_path = CHECKPOINT_DIR / f"crossref_{keyword.replace(' ', '_')}.json"
    start_page = 0
    next_cursor = "*"  # Start with the initial cursor

    if resume:
        checkpoint = load_checkpoint(checkpoint_path)
        if checkpoint:
            if use_cursor:
                next_cursor = checkpoint.get("next_cursor", "*")
                LOGGER.info("断点续跑：从 cursor %s 开始", next_cursor)
            else:
                start_page = checkpoint.get("page", 0)
                LOGGER.info("断点续跑：从第%s页开始", start_page + 1)

    page = start_page
    while page < max_pages:
        params = {
            "query": keyword,
            "rows": rows,
        }
        if use_cursor:
            params["cursor"] = next_cursor
        else:
            params["offset"] = page * rows

        filters = []
        if start_date:
            filters.append(f"from-pub-date:{start_date}")
        if end_date:
            filters.append(f"until-pub-date:{end_date}")
        if article_types:
            # article_types 是逗号分隔的字符串，如 "journal-article,proceedings-article"
            for atype in article_types.split(","):
                atype = atype.strip()
                if atype:
                    filters.append(f"type:{atype}")
        if filters:
            params["filter"] = ",".join(filters)
        if CROSSREF_MAILTO:
            params["mailto"] = CROSSREF_MAILTO
        
        # 注意：Crossref 列表查询 API 不支持 select 返回 author 字段
        # author 必须通过单 DOI 查询获取（见 fix_authors.py 或 multi_source_collector.py）

        resp, sleep_time = request_with_retry(session, CROSSREF_API_URL, params)
        data = resp.json()
        message = data.get("message", {})
        items = message.get("items", [])
        if not items:
            LOGGER.info("无更多数据，提前结束。")
            break
        all_items.extend(items)
        LOGGER.info("已抓取第%s页，累计%s条", page + 1, len(all_items))

        if use_cursor:
            next_cursor = message.get("next-cursor")
            if not next_cursor:
                LOGGER.info("无 next-cursor，采集完成。")
                break
            save_checkpoint(
                checkpoint_path,
                {
                    "next_cursor": next_cursor,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            save_checkpoint(
                checkpoint_path,
                {"page": page + 1, "updated_at": datetime.now(timezone.utc).isoformat()},
            )

        page += 1
        time.sleep(sleep_time)

    return all_items


def fetch_single_doi(doi: str):
    """通过DOI获取单条文献的元数据"""
    session = requests.Session()
    session.headers.update(build_headers())
    
    url = f"{CROSSREF_API_URL}/{doi}"
    params = {}
    if CROSSREF_MAILTO:
        params["mailto"] = CROSSREF_MAILTO
        
    try:
        resp, _ = request_with_retry(session, url, params)
        data = resp.json()
        return data.get("message")
    except RuntimeError as e:
        LOGGER.error("获取DOI %s 失败: %s", doi, e)
        return None


def upsert_paper(cur, item):
    doi = item.get("DOI")
    wos_id = item.get("wos_id")
    if not doi:
        # OA 数据可能没有 DOI，使用 oa_url 作为替代标识
        oa_url = item.get("oa_url")
        if oa_url:
            doi = f"oa:{oa_url}"
        elif wos_id:
            doi = f"wos:{wos_id}"
        else:
            return None

    source = item.get("source", "crossref")
    title = item.get("title")
    if isinstance(title, list):
        title = " ".join(title).strip() or None

    # 处理 author 字段（可能是 JSON 字符串或列表）
    author_data = item.get("author", [])
    if isinstance(author_data, str):
        authors = author_data
    else:
        authors = json.dumps(parse_authors(author_data) if isinstance(author_data, list) else author_data, ensure_ascii=False)

    publisher = item.get("publisher")
    published_date = parse_published_date(item)
    abstract = clean_abstract(item.get("abstract"))

    # 期刊相关字段
    container_title = item.get("container-title", [])
    journal = container_title[0] if container_title else item.get("journal")
    short_container_title = item.get("short-container-title", [])
    journal_abbr = short_container_title[0] if short_container_title else item.get("journal_abbr")
    volume = item.get("volume")
    issue = item.get("issue")
    page = item.get("page")
    issn_list = item.get("ISSN", [])
    issn = issn_list[0] if issn_list else item.get("issn")
    article_type = item.get("type") or item.get("article_type")
    # 标准化 article_type
    if article_type:
        article_type = ARTICLE_TYPE_MAPPING.get(article_type, article_type)
    subject_list = item.get("subject", [])
    if isinstance(subject_list, str):
        subject = subject_list
    else:
        subject = json.dumps(subject_list, ensure_ascii=False) if subject_list else None

    # 关键词与期刊分级
    keywords = item.get("keywords")
    if isinstance(keywords, str):
        pass
    elif keywords:
        keywords = json.dumps(keywords, ensure_ascii=False)
    else:
        keywords = None
    journal_tier = item.get("journal_tier") or get_journal_tier(journal)

    # OA 特有字段
    oa_url = item.get("oa_url")
    oa_category = item.get("oa_category")

    # 多源整合扩展字段
    citation_count = item.get("citation_count")
    wos_times_cited = item.get("wos_times_cited")
    references_count = item.get("references_count")
    language = item.get("language")
    external_ids = item.get("external_ids")
    if external_ids and not isinstance(external_ids, str):
        external_ids = json.dumps(external_ids, ensure_ascii=False)

    meta_json = item.get("meta_json") or json.dumps(item, ensure_ascii=False)

    if is_sqlite():
        sql = f"""
        INSERT INTO papers (doi, wos_id, source, title, author, publisher, published_date, abstract,
            journal, journal_abbr, volume, issue, page, issn, article_type, subject, keywords, journal_tier,
            oa_url, oa_category, citation_count, wos_times_cited, references_count, language, external_ids, meta_json)
        VALUES ({placeholders(26)})
        ON CONFLICT(doi) DO UPDATE SET
            wos_id=excluded.wos_id,
            source=excluded.source,
            title=excluded.title,
            author=excluded.author,
            publisher=excluded.publisher,
            published_date=excluded.published_date,
            abstract=excluded.abstract,
            journal=excluded.journal,
            journal_abbr=excluded.journal_abbr,
            volume=excluded.volume,
            issue=excluded.issue,
            page=excluded.page,
            issn=excluded.issn,
            article_type=excluded.article_type,
            subject=excluded.subject,
            keywords=excluded.keywords,
            journal_tier=excluded.journal_tier,
            oa_url=excluded.oa_url,
            oa_category=excluded.oa_category,
            citation_count=excluded.citation_count,
            wos_times_cited=excluded.wos_times_cited,
            references_count=excluded.references_count,
            language=excluded.language,
            external_ids=excluded.external_ids,
            meta_json=excluded.meta_json;
        """
        cur.execute(sql, (doi, wos_id, source, title, authors, publisher, published_date, abstract,
                         journal, journal_abbr, volume, issue, page, issn, article_type, subject, keywords, journal_tier,
                         oa_url, oa_category, citation_count, wos_times_cited, references_count, language, external_ids, meta_json))
        cur.execute("SELECT id FROM papers WHERE doi = ?", (doi,))
        return cur.fetchone()[0]

    sql = f"""
        INSERT INTO papers (doi, wos_id, source, title, author, publisher, published_date, abstract,
            journal, journal_abbr, volume, issue, page, issn, article_type, subject, keywords, journal_tier,
            oa_url, oa_category, citation_count, wos_times_cited, references_count, language, external_ids, meta_json)
        VALUES ({placeholders(26)})
        ON CONFLICT (doi) DO UPDATE SET
            wos_id = EXCLUDED.wos_id,
            source = EXCLUDED.source,
            title = EXCLUDED.title,
            author = EXCLUDED.author,
            publisher = EXCLUDED.publisher,
            published_date = EXCLUDED.published_date,
            abstract = EXCLUDED.abstract,
            journal = EXCLUDED.journal,
            journal_abbr = EXCLUDED.journal_abbr,
            volume = EXCLUDED.volume,
            issue = EXCLUDED.issue,
            page = EXCLUDED.page,
            issn = EXCLUDED.issn,
            article_type = EXCLUDED.article_type,
            subject = EXCLUDED.subject,
            keywords = EXCLUDED.keywords,
            journal_tier = EXCLUDED.journal_tier,
            oa_url = EXCLUDED.oa_url,
            oa_category = EXCLUDED.oa_category,
            citation_count = EXCLUDED.citation_count,
            wos_times_cited = EXCLUDED.wos_times_cited,
            references_count = EXCLUDED.references_count,
            language = EXCLUDED.language,
            external_ids = EXCLUDED.external_ids,
            meta_json = EXCLUDED.meta_json
        RETURNING id;
        """
    cur.execute(sql, (doi, wos_id, source, title, authors, publisher, published_date, abstract,
                     journal, journal_abbr, volume, issue, page, issn, article_type, subject, keywords, journal_tier,
                     oa_url, oa_category, citation_count, wos_times_cited, references_count, language, external_ids, meta_json))
    return cur.fetchone()[0]


def upsert_funder(cur, funder):
    sql = f"""
        INSERT INTO funders (doi, name, award)
        VALUES ({placeholders(3)})
        ON CONFLICT (doi, name) DO UPDATE SET award = excluded.award
        {"RETURNING id" if not is_sqlite() else ""};
        """
    cur.execute(
        sql,
        (funder.get("doi"), funder.get("name"), json.dumps(funder.get("award"), ensure_ascii=False)),
    )
    if is_sqlite():
        cur.execute("SELECT id FROM funders WHERE doi = ? AND name = ?", (funder.get("doi"), funder.get("name")))
        return cur.fetchone()[0]
    return cur.fetchone()[0]


def upsert_license(cur, license_item):
    sql = f"""
        INSERT INTO licenses (url, content_version, start_date)
        VALUES ({placeholders(3)})
        ON CONFLICT (url, content_version) DO UPDATE SET start_date = excluded.start_date
        {"RETURNING id" if not is_sqlite() else ""};
        """
    cur.execute(
        sql,
        (license_item.get("url"), license_item.get("content_version"), license_item.get("start_date")),
    )
    if is_sqlite():
        cur.execute(
            "SELECT id FROM licenses WHERE url = ? AND content_version = ?",
            (license_item.get("url"), license_item.get("content_version")),
        )
        return cur.fetchone()[0]
    return cur.fetchone()[0]


def upsert_relation(cur, relation):
    sql = f"""
        INSERT INTO relations (relation_type, relation_id, relation_id_type, asserted_by)
        VALUES ({placeholders(4)})
        ON CONFLICT (relation_type, relation_id, relation_id_type, asserted_by)
        DO UPDATE SET asserted_by = excluded.asserted_by
        {"RETURNING id" if not is_sqlite() else ""};
        """
    cur.execute(
        sql,
        (relation.get("type"), relation.get("id"), relation.get("id_type"), relation.get("asserted_by")),
    )
    if is_sqlite():
        cur.execute(
            "SELECT id FROM relations WHERE relation_type = ? AND relation_id = ? AND relation_id_type = ? AND asserted_by = ?",
            (relation.get("type"), relation.get("id"), relation.get("id_type"), relation.get("asserted_by")),
        )
        return cur.fetchone()[0]
    return cur.fetchone()[0]


def upsert_link(cur, link):
    sql = f"""
        INSERT INTO links (url, content_type, content_version, intended_application)
        VALUES ({placeholders(4)})
        ON CONFLICT (url, content_type, content_version, intended_application)
        DO UPDATE SET intended_application = excluded.intended_application
        {"RETURNING id" if not is_sqlite() else ""};
        """
    cur.execute(
        sql,
        (
            link.get("url"),
            link.get("content_type"),
            link.get("content_version"),
            link.get("intended_application"),
        ),
    )
    if is_sqlite():
        cur.execute(
            "SELECT id FROM links WHERE url = ? AND content_type = ? AND content_version = ? AND intended_application = ?",
            (
                link.get("url"),
                link.get("content_type"),
                link.get("content_version"),
                link.get("intended_application"),
            ),
        )
        return cur.fetchone()[0]
    return cur.fetchone()[0]


def upsert_citation(cur, citing_doi, cited_doi):
    sql = f"""
    INSERT INTO citations (citing_doi, cited_doi)
    VALUES ({placeholders(2)})
    ON CONFLICT DO NOTHING;
    """
    cur.execute(sql, (citing_doi, cited_doi))


def save_to_db(conn, items):
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    for item in items:
        try:
            paper_id = upsert_paper(cur, item)
            if not paper_id:
                skipped += 1
                continue

            for funder in parse_funders(item.get("funder", [])):
                if not funder.get("doi") or not funder.get("name"):
                    continue
                funder_id = upsert_funder(cur, funder)
                if funder_id:
                    cur.execute(
                        f"""
                        INSERT INTO paper_funders (paper_id, funder_id)
                        VALUES ({placeholders(2)})
                        ON CONFLICT DO NOTHING;
                        """,
                        (paper_id, funder_id),
                    )

            for license_item in parse_licenses(item.get("license", [])):
                if not license_item.get("url"):
                    continue
                license_id = upsert_license(cur, license_item)
                if license_id:
                    cur.execute(
                        f"""
                        INSERT INTO paper_licenses (paper_id, license_id)
                        VALUES ({placeholders(2)})
                        ON CONFLICT DO NOTHING;
                        """,
                        (paper_id, license_id),
                    )

            for relation in parse_relations(item.get("relation", {})):
                if not relation.get("id") or not relation.get("id_type"):
                    continue
                relation_id = upsert_relation(cur, relation)
                if relation_id:
                    cur.execute(
                        f"""
                        INSERT INTO paper_relations (paper_id, relation_id)
                        VALUES ({placeholders(2)})
                        ON CONFLICT DO NOTHING;
                        """,
                        (paper_id, relation_id),
                    )

                # 提取引用关系
                if relation.get("id_type") == "doi" and relation.get("type") in ("cites", "references"):
                    upsert_citation(cur, item.get("DOI"), relation.get("id"))

            # 从 reference 字段提取引用
            for ref in item.get("reference", []):
                if ref.get("DOI"):
                    upsert_citation(cur, item.get("DOI"), ref.get("DOI"))

            for link in parse_links(item.get("link", [])):
                if not link.get("url"):
                    continue
                link_id = upsert_link(cur, link)
                if link_id:
                    cur.execute(
                        f"""
                        INSERT INTO paper_links (paper_id, link_id)
                        VALUES ({placeholders(2)})
                        ON CONFLICT DO NOTHING;
                        """,
                        (paper_id, link_id),
                    )

            # 作者消歧与统一
            try:
                resolve_paper(paper_id, item.get("author"), conn)
            except Exception as e:
                LOGGER.warning("作者消歧失败 (paper_id=%s): %s", paper_id, e)

            inserted += 1
            conn.commit()
        except Exception as e:
            LOGGER.warning("入库失败：%s", e)
            skipped += 1
            conn.rollback()

    cur.close()
    LOGGER.info("入库完成，新增/更新 %s 条，跳过 %s 条", inserted, skipped)
    return {"inserted": inserted, "skipped": skipped}


def save_to_postgres(items, db_config):
    conn = get_connection(init_schema=True)
    try:
        return save_to_db(conn, items)
    finally:
        conn.close()


def save_raw_json(items, keyword):
    RAW_JSON_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = RAW_JSON_DIR / f"crossref_{keyword.replace(' ', '_')}_{timestamp}.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_fetch(keyword, rows=100, max_pages=10, start_date=None, end_date=None):
    """
    可导出的 Crossref 采集函数（供其他模块调用）
    返回：入库的记录数
    """
    items = fetch_crossref_metadata(
        keyword,
        rows,
        max_pages,
        start_date,
        end_date,
        resume=False,
        use_cursor=False,
    )

    # 标准化 Crossref 原始数据
    normalized_items = [normalize_crossref_item(item) for item in items]

    # 入库
    db_report = save_to_postgres(normalized_items, DB_CONFIG)
    return db_report.get("inserted", len(items))


def save_report(report, keyword):
    RAW_JSON_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = RAW_JSON_DIR / f"crossref_report_{keyword.replace(' ', '_')}_{timestamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args():
    parser = argparse.ArgumentParser(description="Crossref 采集与入库")
    parser.add_argument("--keyword", default=KEYWORD)
    parser.add_argument("--rows", type=int, default=ROWS_PER_PAGE)
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    parser.add_argument("--start-date", default=CROSSREF_START_DATE)
    parser.add_argument("--end-date", default=CROSSREF_END_DATE)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-raw", action="store_true")
    parser.add_argument("--use-cursor", action="store_true", help="使用游标进行分页")
    parser.add_argument(
        "--article-types",
        default=ARTICLE_TYPES_FILTER,
        help="逗号分隔的 Article Type 列表，用于过滤结果。如: journal-article,proceedings-article",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    items = fetch_crossref_metadata(
        args.keyword,
        args.rows,
        args.max_pages,
        args.start_date,
        args.end_date,
        args.resume,
        args.use_cursor,
        args.article_types,
    )

    # 标准化 Crossref 原始数据，提取 external_ids、oa_category、oa_url 等字段
    normalized_items = [normalize_crossref_item(item) for item in items]

    report = {}
    if not args.no_raw:
        raw_path = save_raw_json(normalized_items, args.keyword)
        report["raw_json_path"] = str(raw_path)

    db_report = save_to_postgres(normalized_items, DB_CONFIG)
    report.update(db_report)

    report_path = save_report(report, args.keyword)
    LOGGER.info("报告已保存：%s", report_path)


if __name__ == "__main__":
    main()
