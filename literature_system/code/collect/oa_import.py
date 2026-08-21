"""
数据采集并入库到统一数据库
支持多种数据源：arXiv, PMC, OpenAlex, Semantic Scholar, PubMed
"""
import sys
from pathlib import Path

# 确保能找到 code/ 目录下的模块
_CODE_ROOT = Path(__file__).resolve().parent.parent
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

import argparse
import sqlite3

from config import SQLITE_PATH
from logger import get_logger
from sources.arxiv import ArxivAdapter
from sources.pmc import PmcAdapter
from sources.openalex import OpenAlexAdapter
from sources.semantic_scholar import SemanticScholarAdapter
from sources.pubmed import PubmedAdapter
from sources.wos import WosAdapter
from sources.scopus import ScopusAdapter
from utils import get_journal_tier
from author.author_resolution import resolve_paper
from db import get_connection

LOGGER = get_logger("data_import")

def parse_authors_from_json(author_str):
    """从 JSON 字符串解析作者"""
    import json
    try:
        authors = json.loads(author_str)
        return json.dumps(authors, ensure_ascii=False)
    except:
        return author_str

def upsert_paper(cur, item):
    """将单条数据插入数据库"""
    import json

    doi = item.get("DOI")
    wos_id = item.get("wos_id")
    if not doi:
        oa_url = item.get("oa_url")
        if oa_url:
            doi = f"oa:{oa_url}"
        elif wos_id:
            doi = f"wos:{wos_id}"
        else:
            return None

    source = item.get("source", "unknown")
    title = item.get("title")
    if isinstance(title, list):
        title = " ".join(title).strip() or None

    author_data = item.get("author", [])
    if isinstance(author_data, str):
        authors = author_data
    else:
        authors = json.dumps(author_data, ensure_ascii=False)

    publisher = item.get("publisher")
    published_date = item.get("published_date")
    abstract = item.get("abstract")

    journal = item.get("journal")
    journal_abbr = item.get("journal_abbr")
    volume = item.get("volume")
    issue = item.get("issue")
    page = item.get("page")
    issn = item.get("issn")
    article_type = item.get("article_type")

    subject = item.get("subject")
    if subject and not isinstance(subject, str):
        subject = json.dumps(subject, ensure_ascii=False)

    keywords = item.get("keywords")
    if isinstance(keywords, str):
        pass
    elif keywords:
        keywords = json.dumps(keywords, ensure_ascii=False)
    else:
        keywords = None

    # 期刊分级
    journal_tier = item.get("journal_tier") or get_journal_tier(journal)

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

    meta_json = item.get("meta_json")
    if meta_json and not isinstance(meta_json, str):
        meta_json = json.dumps(meta_json, ensure_ascii=False)

    sql = """
    INSERT INTO papers (doi, wos_id, source, title, author, publisher, published_date, abstract,
        journal, journal_abbr, volume, issue, page, issn, article_type, subject, keywords, journal_tier,
        oa_url, oa_category, citation_count, wos_times_cited, references_count, language, external_ids, meta_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    row = cur.fetchone()
    return row[0] if row else None

def fetch_and_import(
    source,
    keyword,
    page_size,
    max_pages,
    start_date=None,
    end_date=None,
    return_details=False,
):
    """采集数据并导入数据库"""
    adapter_classes = {
        "arxiv": ArxivAdapter,
        "pmc": PmcAdapter,
        "openalex": OpenAlexAdapter,
        "semanticscholar": SemanticScholarAdapter,
        "pubmed": PubmedAdapter,
        "wos": WosAdapter,
        "scopus": ScopusAdapter,
    }

    if source not in adapter_classes:
        raise ValueError(f"Unknown source: {source}")

    adapter = adapter_classes[source]()
    conn = get_connection(init_schema=True)
    cur = conn.cursor()

    total_inserted = 0
    paper_ids = []
    for page in range(max_pages):
        LOGGER.info("%s 正在抓取第 %s 页...", source, page + 1)
        items = adapter.fetch(keyword, page, page_size, start_date=start_date, end_date=end_date)
        if not items:
            LOGGER.info("%s 第 %s 页无数据，停止", source, page + 1)
            break

        for item in items:
            try:
                paper_id = upsert_paper(cur, item)
                if paper_id:
                    paper_ids.append(int(paper_id))
                    try:
                        resolve_paper(paper_id, item.get("author"), conn)
                    except Exception as e:
                        LOGGER.warning("作者消歧失败 (paper_id=%s): %s", paper_id, e)
                    total_inserted += 1
            except Exception as e:
                LOGGER.warning("入库失败：%s", e)

        conn.commit()
        LOGGER.info("%s 第 %s 页：导入 %s 条", source, page + 1, len(items))

    cur.close()
    conn.close()
    LOGGER.info("%s 入库完成，共导入 %s 条", source, total_inserted)
    if return_details:
        return {
            "source": source,
            "processed": total_inserted,
            "paper_ids": list(dict.fromkeys(paper_ids)),
        }
    return total_inserted


def fetch_all_sources(keyword, page_size, max_pages, start_date=None, end_date=None):
    """从所有数据源采集并导入数据库"""
    all_sources = ["crossref", "arxiv", "pmc", "openalex", "semanticscholar", "pubmed", "wos", "scopus"]
    results = {}

    for source in all_sources:
        LOGGER.info("=" * 50)
        LOGGER.info("开始采集数据源: %s", source)
        LOGGER.info("=" * 50)

        try:
            if source == "crossref":
                # Crossref 使用独立的 fetch_and_save 模块
                from collect.fetch_and_save import run_fetch
                count = run_fetch(keyword, page_size, max_pages, start_date, end_date)
            else:
                count = fetch_and_import(source, keyword, page_size, max_pages, start_date, end_date)
            results[source] = count
        except Exception as e:
            LOGGER.error("数据源 %s 采集失败: %s", source, e)
            results[source] = 0

    LOGGER.info("=" * 50)
    LOGGER.info("所有数据源采集完成!")
    LOGGER.info("=" * 50)
    for source, count in results.items():
        LOGGER.info("  %s: %s 条", source, count)
    return results


def main():
    parser = argparse.ArgumentParser(description="数据采集入库（支持多数据源）")
    parser.add_argument("--source", choices=[
        "all", "arxiv", "pmc", "openalex", "semanticscholar", "pubmed", "wos", "scopus"
    ], default="all", help="数据源：all(默认), arxiv, pmc, openalex, semanticscholar, pubmed, wos, scopus")
    parser.add_argument("--keyword", required=True, help="搜索关键词")
    parser.add_argument("--page-size", type=int, default=50, help="每页条数（Crossref 默认 100）")
    parser.add_argument("--max-pages", type=int, default=3, help="最大页数")
    parser.add_argument("--start-date", help="开始日期 (YYYY-MM-DD)，仅支持部分数据源")
    parser.add_argument("--end-date", help="结束日期 (YYYY-MM-DD)，仅支持部分数据源")
    args = parser.parse_args()

    if args.source == "all":
        fetch_all_sources(args.keyword, args.page_size, args.max_pages,
                         start_date=args.start_date, end_date=args.end_date)
    else:
        fetch_and_import(args.source, args.keyword, args.page_size, args.max_pages,
                       start_date=args.start_date, end_date=args.end_date)

if __name__ == "__main__":
    main()
