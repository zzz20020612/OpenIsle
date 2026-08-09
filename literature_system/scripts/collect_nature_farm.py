"""采集 Nature 系列期刊近 3 年 farm/agriculture/livestock 相关论文。

用法:
    python scripts/collect_nature_farm.py --target 10
    python scripts/collect_nature_farm.py --target 10 --dry-run  # 仅搜索不入库
"""
import sys
from pathlib import Path

_CODE_ROOT = Path(__file__).resolve().parent.parent / "code"
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

import argparse
import json
import time
from datetime import datetime

import requests

from config import (
    CROSSREF_API_URL,
    CROSSREF_MAILTO,
    CROSSREF_USER_AGENT,
    SQLITE_PATH,
)
from db import get_connection
from collect.multi_source_collector import upsert_paper

# Nature 系列期刊 ISSN（print + electronic）
NATURE_ISSNS = [
    # Nature 主刊
    "0028-0836", "1476-4687",
    # Nature Communications
    "2041-1723",
    # Nature Climate Change
    "1758-678X", "1758-6798",
    # Nature Sustainability
    "2398-9629",
    # Nature Food
    "2662-1355",
    # Nature Ecology & Evolution
    "2397-334X",
    # Nature Plants
    "2055-0278",
    # Nature Microbiology
    "2058-5276",
    # Nature Geoscience
    "1752-0894", "1752-0908",
    # Nature Biotechnology
    "1087-0156", "1546-1696",
    # Nature Genetics
    "1061-4036", "1546-1718",
    # Nature Medicine
    "1078-8956", "1546-170X",
    # Scientific Reports
    "2045-2322",
    # Communications Biology
    "2399-3642",
    # Communications Earth & Environment
    "2662-4435",
    # Nature Water
    "2731-6084",
    # Nature Chemical Biology
    "1552-4450", "1552-4469",
    # Nature Metabolism
    "2522-5812",
    # Nature Aging
    "2662-8465",
    # Nature Computational Science
    "2662-8457",
    # Nature Machine Intelligence
    "2522-5839",
    # npj 系列
    "2059-7037",  # npj Science of Food
    "2056-3068",  # npj Biofilms and Microbiomes
    "2397-3366",  # npj Clean Water
]

# farm 相关关键词
KEYWORDS = [
    "farm", "farming", "agriculture", "livestock", "cattle",
    "cropland", "pasture", "agroecology", "soil health",
    "sustainable agriculture", "food security",
]


def search_crossref_nature(keyword: str, rows: int = 20, start_year: int = 2024):
    """搜索 Crossref 获取 Nature 系列期刊论文。"""
    issn_filter = ",".join(f"issn:{i}" for i in NATURE_ISSNS[:30])  # 限制 ISSN 数量避免 URL 过长
    url = CROSSREF_API_URL
    params = {
        "query": keyword,
        "rows": rows,
        "filter": f"{issn_filter},from-pub-date:{start_year}-01-01,type:journal-article",
        "select": "DOI,title,author,publisher,created,abstract,container-title,type,link,ISSN",
        "sort": "relevance",
    }
    if CROSSREF_MAILTO:
        params["mailto"] = CROSSREF_MAILTO

    headers = {"User-Agent": CROSSREF_USER_AGENT}
    print(f"  搜索关键词: {keyword} (rows={rows})")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        print(f"  返回 {len(items)} 条结果")
        return items
    except Exception as e:
        print(f"  搜索失败: {e}")
        return []


def normalize_crossref_to_item(msg: dict) -> dict:
    """将 Crossref API 返回的 message 转为 upsert_paper 所需的 item 格式。"""
    doi = msg.get("DOI")
    title = msg.get("title", [])
    if isinstance(title, list):
        title = title[0] if title else ""
    abstract = msg.get("abstract", "")
    publisher = msg.get("publisher", "")
    journal = msg.get("container-title", [])
    if isinstance(journal, list):
        journal = journal[0] if journal else ""

    # 日期
    created = msg.get("created", {})
    if isinstance(created, dict):
        date_parts = created.get("date-parts", [[None]])[0]
        published_date = "-".join(str(p) for p in date_parts if p) if date_parts else None
    else:
        published_date = None

    # 构建 author 列表
    author_raw = msg.get("author", [])
    author_list = []
    for a in author_raw:
        given = a.get("given", "")
        family = a.get("family", "")
        if given and family:
            author_list.append({"given": given, "family": family})
        elif family:
            author_list.append({"family": family})

    # OA URL
    oa_url = ""
    links = msg.get("link", [])
    for link in links:
        if link.get("content-type") == "application/pdf":
            oa_url = link.get("URL", "")
            break

    return {
        "DOI": doi,
        "title": title,
        "abstract": abstract,
        "publisher": publisher,
        "journal": journal,
        "published_date": published_date,
        "author": author_list,
        "type": msg.get("type", "journal-article"),
        "oa_url": oa_url,
        "oa_category": "",
    }


def collect_nature_farm(target: int = 10, dry_run: bool = False):
    """采集 Nature 系列 farm 相关论文。"""
    all_items = []
    seen_dois = set()

    print(f"=== Nature 系列 farm 论文采集（目标 {target} 篇，{2024}-2026 年）===\n")

    for keyword in KEYWORDS:
        if len(all_items) >= target * 2:  # 多搜一些以备筛选
            break
        items = search_crossref_nature(keyword, rows=20, start_year=2024)
        for item in items:
            doi = item.get("DOI")
            if doi and doi not in seen_dois:
                seen_dois.add(doi)
                normalized = normalize_crossref_to_item(item)
                all_items.append(normalized)
        time.sleep(0.5)  # polite delay

    print(f"\n去重后共 {len(all_items)} 篇候选论文")

    if dry_run:
        print("\n=== 预览（不入库）===")
        for i, item in enumerate(all_items[:target]):
            print(f"\n[{i+1}] DOI: {item.get('DOI')}")
            print(f"    标题: {item.get('title', '')[:100]}")
            print(f"    期刊: {item.get('journal', '')}")
            print(f"    日期: {item.get('published_date', '')}")
            print(f"    OA: {item.get('oa_url', '无')}")
        return

    # 入库
    conn = get_connection(init_schema=False)
    inserted = 0
    try:
        for item in all_items[:target]:
            paper_id = upsert_paper(conn, item, source="nature_crossref")
            doi = item.get("DOI") or "(no DOI)"
            title = item.get("title") or "(no title)"
            if paper_id:
                inserted += 1
                print(f"[✓] 入库 paper_id={paper_id} | {doi} | {str(title)[:80]}")
            else:
                print(f"[✗] 跳过 | {doi} | {str(title)[:80]}")
            if inserted >= target:
                break
    finally:
        conn.close()

    print(f"\n共入库 {inserted} 篇论文（目标 {target} 篇）")
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nature 系列 farm 论文采集")
    parser.add_argument("--target", type=int, default=10, help="目标采集数量")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不入库")
    args = parser.parse_args()
    collect_nature_farm(args.target, args.dry_run)