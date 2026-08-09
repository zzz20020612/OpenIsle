"""回填已有 Crossref 论文的 oa_url。

问题：multi_source_collector.upsert_paper 之前未写入 oa_url，导致 Crossref 采集的论文
全部缺失 PDF 直链。本脚本：
1. 先从 meta_json 的 link/license 字段提取 oa_url；
2. 若仍无，则调用 Unpaywall API 查询最佳 OA PDF 链接。
"""
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'code'))

from config import CROSSREF_MAILTO
from db import get_connection
from logger import get_logger

LOGGER = get_logger("fix_crossref_oa_url")

UNPAYWALL_EMAIL = CROSSREF_MAILTO or "research@example.com"


def extract_oa_url_from_crossref(item: dict):
    """从 Crossref item 提取 PDF 直链与开放获取类型。"""
    links = item.get("link", []) or []
    oa_url = None
    for link in links:
        content_type = link.get("content-type", "")
        intended_app = link.get("intended-application", "")
        url = link.get("URL", "")
        if "pdf" in content_type.lower() or "pdf" in intended_app.lower():
            oa_url = url
            break
        elif "xml" in content_type.lower() or "text/xml" in content_type.lower():
            if not oa_url:
                oa_url = url

    oa_category = None
    licenses = item.get("license", []) or []
    for lic in licenses:
        content_version = lic.get("content-version", "").lower()
        if content_version in ("vor", "published"):
            oa_category = "publisher-gold"
            break
        elif content_version == "tdm":
            oa_category = "tdm"
            break
    if not oa_category and item.get("is-open-access"):
        oa_category = "open-access"

    return oa_url or "", oa_category or ""


def fetch_unpaywall_url(doi: str) -> str:
    """通过 Unpaywall API 查询 DOI 的最佳 OA PDF 链接。"""
    if not doi:
        return ""
    try:
        url = f"https://api.unpaywall.org/v2/{doi}"
        params = {"email": UNPAYWALL_EMAIL}
        headers = {"User-Agent": "LiteratureSystem/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            best = data.get("best_oa_location") or {}
            pdf_url = best.get("url_for_pdf") or best.get("url")
            if pdf_url:
                return pdf_url
            for loc in data.get("oa_locations", []) or []:
                if loc.get("url_for_pdf"):
                    return loc["url_for_pdf"]
                if loc.get("url"):
                    return loc["url"]
        else:
            LOGGER.warning("Unpaywall %s 返回 %s", doi, resp.status_code)
    except Exception as e:
        LOGGER.warning("Unpaywall %s 查询失败: %s", doi, e)
    return ""


def get_crossref_papers_without_oa():
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, doi, meta_json FROM papers
            WHERE source = 'crossref' AND (oa_url IS NULL OR oa_url = '')
            ORDER BY id
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_oa_url(paper_id, oa_url, oa_category):
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE papers SET oa_url=?, oa_category=? WHERE id=?",
            (oa_url, oa_category, paper_id),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def main():
    papers = get_crossref_papers_without_oa()
    LOGGER.info("发现 %d 条 Crossref 论文缺失 oa_url", len(papers))

    fixed_crossref = 0
    fixed_unpaywall = 0
    no_oa = 0

    for p in papers:
        paper_id = p["id"]
        doi = p["doi"]
        meta = p["meta_json"]

        # 1. 尝试从 Crossref meta_json 提取
        oa_url = ""
        oa_category = ""
        if meta:
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    LOGGER.warning("paper_id=%d DOI=%s meta_json 解析失败", paper_id, doi)
                    meta = None
            if meta:
                oa_url, oa_category = extract_oa_url_from_crossref(meta)

        # 2. Crossref 无 link 时，调用 Unpaywall
        if not oa_url and doi:
            oa_url = fetch_unpaywall_url(doi)
            if oa_url:
                oa_category = oa_category or "unpaywall"
            # 礼貌请求，避免触发限流
            time.sleep(0.2)

        if oa_url:
            update_oa_url(paper_id, oa_url, oa_category)
            LOGGER.info("paper_id=%d DOI=%s 已回填 oa_url=%s", paper_id, doi, oa_url[:80])
            if oa_category == "unpaywall":
                fixed_unpaywall += 1
            else:
                fixed_crossref += 1
        else:
            LOGGER.info("paper_id=%d DOI=%s 无可用 oa_url", paper_id, doi)
            no_oa += 1

    LOGGER.info("\n完成：Crossref 回填 %d 条, Unpaywall 回填 %d 条, 无可用 %d 条",
                fixed_crossref, fixed_unpaywall, no_oa)


if __name__ == "__main__":
    main()
