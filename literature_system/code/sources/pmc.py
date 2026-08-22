from __future__ import annotations

import json
import re
from datetime import datetime
from xml.etree import ElementTree
from .base import SourceAdapter


def _parse_oa_package_url(xml: str) -> str | None:
    """Return the official HTTPS OA package URL, or None for non-OA records."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return None
    for link in root.findall(".//link"):
        if link.attrib.get("format") != "tgz":
            continue
        href = link.attrib.get("href", "").strip()
        if href.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
            return "https://ftp.ncbi.nlm.nih.gov/" + href.removeprefix(
                "ftp://ftp.ncbi.nlm.nih.gov/"
            )
        if href.startswith("https://"):
            return href
    return None


def _parse_pmc_pubdate(pubdate: str) -> str:
    """将 PMC esummary 返回的多种日期格式标准化为 YYYY-MM-DD。"""
    if not pubdate:
        return None
    pubdate = pubdate.strip()
    # 2020 Jan 15
    m = re.match(r"(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})", pubdate)
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%Y %b %d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 2020 Jan
    m = re.match(r"(\d{4})\s+([A-Za-z]{3})\b", pubdate)
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)} 01", "%Y %b %d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 2020
    m = re.match(r"(\d{4})\b", pubdate)
    if m:
        return f"{m.group(1)}-01-01"
    return None


class PmcAdapter(SourceAdapter):
    name = "pmc"

    def fetch(self, keyword: str, page: int, page_size: int, start_date: str = None, end_date: str = None):
        retstart = page * page_size
        
        # PMC 日期过滤：在搜索词中添加日期范围
        date_filter = ""
        if start_date:
            # 格式: (start[dp] : end[dp]) 
            date_filter = f" AND ({start_date}[dp] : {end_date or '3000'}[dp])" if end_date else f" AND ({start_date}[dp] : 3000[dp])"
        
        search_params = {
            "db": "pmc",
            "term": keyword + date_filter,
            "retstart": retstart,
            "retmax": page_size,
            "retmode": "json",
        }
        search_resp = self.request_with_retry(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params=search_params,
            timeout=30,
        )
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        summary_resp = self.request_with_retry(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pmc", "id": ",".join(ids), "retmode": "json"},
            timeout=30,
        )
        result = summary_resp.json().get("result", {})

        items = []
        for pmc_id in ids:
            item_data = result.get(pmc_id)
            if not item_data:
                continue

            oa_response = self.request_with_retry(
                "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi",
                params={"id": f"PMC{pmc_id}"},
                timeout=30,
            )
            oa_package_url = _parse_oa_package_url(oa_response.text)
            if not oa_package_url:
                continue

            # 解析作者
            authors = []
            for author in item_data.get("authors", []):
                authors.append({
                    "given": author.get("name", "").split()[-1] if author.get("name") else "",
                    "family": author.get("name", "").split()[0] if author.get("name") else "",
                    "affiliation": author.get("affiliation", "")
                })

            # PMC 的 DOI
            doi = item_data.get("elocationid", "").replace("doi: ", "") if item_data.get("elocationid") else None

            # PMC 特有的 PubMed ID
            pmid = item_data.get("pmuid")

            # 获取期刊信息（有些 PMC 文章有）
            source = item_data.get("source", "")
            volume = item_data.get("volume", "")
            issue = item_data.get("issue", "")
            pages = item_data.get("pages", "")
            pubtype = "; ".join(item_data.get("pubtype", [])) if item_data.get("pubtype") else ""

            item = {
                "DOI": doi,
                "source": "pmc",
                "title": item_data.get("title"),
                "author": json.dumps(authors, ensure_ascii=False),
                "publisher": "PMC",  # PMC 是 PubMed Central 的缩写
                "published_date": _parse_pmc_pubdate(item_data.get("pubdate", "")),
                "abstract": None,  # PMC summary API 不返回摘要
                # 期刊相关（如果有的话）
                "journal": source,
                "journal_abbr": source,
                "volume": volume,
                "issue": issue,
                "page": pages,
                "issn": item_data.get("issn", ""),
                "article_type": pubtype,
                "subject": json.dumps(item_data.get("doctype", []), ensure_ascii=False) if item_data.get("doctype") else None,
                # PMC OA API 提供官方压缩包，下载器会安全提取其中的主 PDF。
                "oa_url": oa_package_url,
                "oa_category": item_data.get("pubtype", [None])[0] if item_data.get("pubtype") else None,
                # 原始数据
                "meta_json": json.dumps({
                    "pmcid": pmc_id,
                    "pmid": pmid,
                    "title": item_data.get("title"),
                    "source": source,
                    "volume": volume,
                    "issue": issue,
                    "pages": pages,
                    "pubdate": item_data.get("pubdate"),
                    "pubtype": item_data.get("pubtype"),
                    "authors": item_data.get("authors"),
                    "doctype": item_data.get("doctype"),
                }, ensure_ascii=False)
            }
            items.append(item)
        return items
