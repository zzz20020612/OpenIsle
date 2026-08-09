"""
Scopus 数据源适配器（Elsevier API）

说明：
- Scopus API 为商业 API，需要 Elsevier 颁发的 API Key（部分机构还需 Insttoken）。
- 支持多 Key 轮询，当某个 Key 触发配额限制时自动切换到下一个 Key。
- 当前实现基于 Scopus Search API；如需摘要，可再调 Abstract Retrieval API 二次 enrichment。
"""
import os
import time
from typing import List, Optional

from .base import SourceAdapter

try:
    from .. import config
    from ..logger import get_logger
    from ..utils import normalize_orcid
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    from logger import get_logger
    from utils import normalize_orcid

LOGGER = get_logger("scopus")


class ScopusAdapter(SourceAdapter):
    name = "scopus"
    SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
    ABSTRACT_URL = "https://api.elsevier.com/content/abstract/eid/"

    def __init__(self):
        self.api_keys = list(config.SCOPUS_API_KEYS)
        if not self.api_keys:
            raise RuntimeError("未配置 SCOPUS_API_KEYS，无法调用 Scopus API")
        self.current_key_index = 0

    def _current_key(self) -> str:
        return self.api_keys[self.current_key_index]

    def _rotate_key(self):
        """切换到下一个 API Key。"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self._current_key(),
        }
        if config.SCOPUS_INSTTOKEN:
            headers["X-ELS-Insttoken"] = config.SCOPUS_INSTTOKEN
        return headers

    def _request(self, url, params, max_key_rotations=None):
        """支持多 Key 轮询的请求封装。"""
        if max_key_rotations is None:
            max_key_rotations = len(self.api_keys)

        for _ in range(max_key_rotations):
            headers = self._get_headers()
            resp = self.request_with_retry(url, params, headers=headers, timeout=60)

            # Elsevier 配额超限常见返回 429，也可能返回 401/403
            if resp.status_code == 429:
                self._rotate_key()
                time.sleep(1)
                continue

            # 某些情况下会返回 XML 错误信息，需检查 content-type
            content_type = resp.headers.get("content-type", "")
            if "application/json" not in content_type:
                # 尝试切换 key 重试
                self._rotate_key()
                time.sleep(1)
                continue

            return resp

        raise RuntimeError("所有 Scopus API Key 均触发配额限制或返回异常")

    def _build_query(
        self,
        keyword: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """构造 Scopus 检索式。"""
        query = keyword.strip()
        # 若用户已传入完整字段检索式，则保持原样；否则包装为 TITLE-ABS-KEY
        if not any(query.upper().startswith(prefix) for prefix in (
            "TITLE-ABS-KEY", "TITLE", "ABS", "KEY", "DOI", "SRCTITLE", "AUTH", "AFFIL", "PUBYEAR"
        )):
            query = f"TITLE-ABS-KEY({query})"

        date_parts = []
        if start_date:
            date_parts.append(f"PUBYEAR AFT {int(start_date[:4]) - 1}")
        if end_date:
            date_parts.append(f"PUBYEAR BEF {int(end_date[:4]) + 1}")
        if date_parts:
            query = f"{query} AND {' AND '.join(date_parts)}"
        return query

    def fetch(
        self,
        keyword: str,
        page: int = 0,
        page_size: int = 25,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """
        从 Scopus Search API 检索文献。

        Args:
            keyword: 检索词或 Scopus 高级检索式
            page: 页码（从 0 开始）
            page_size: 每页条数（Scopus 通常最大 25）
            start_date/end_date: 日期过滤，取年份部分
        """
        page_size = min(page_size, 25)
        start = page * page_size

        query = self._build_query(keyword, start_date, end_date)
        params = {
            "query": query,
            "start": start,
            "count": page_size,
            # 返回字段：尽量覆盖标题、作者、DOI、期刊、被引等
            "field": "dc:identifier,eid,dc:title,dc:creator,author,prism:publicationName,prism:issn,prism:eIssn,prism:volume,prism:issueIdentifier,prism:pageRange,prism:coverDate,prism:coverDisplayDate,prism:doi,prism:aggregationType,subtype,subtypeDescription,citedby-count,openaccessFlag,affiliation",
        }

        resp = self._request(self.SEARCH_URL, params)
        data = resp.json()

        search_results = data.get("search-results", {}) or {}
        entries = search_results.get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]

        records = []
        for entry in entries:
            parsed = self._parse_entry(entry)
            if parsed:
                records.append(parsed)

        # 通过 Abstract Retrieval API 二次补全摘要
        for record in records:
            eid = (record.get("external_ids") or {}).get("scopus_eid")
            if not eid:
                continue
            try:
                abstract = self.fetch_abstract(eid)
                if abstract:
                    record["abstract"] = abstract
            except Exception as exc:
                LOGGER.warning("Scopus 摘要补全失败 (eid=%s): %s", eid, exc)
            time.sleep(config.SCOPUS_SLEEP_BETWEEN)

        time.sleep(config.SCOPUS_SLEEP_BETWEEN)
        return records

    def _parse_entry(self, entry: dict) -> Optional[dict]:
        """将 Scopus 单条记录解析为项目统一字段。"""
        eid = entry.get("eid") or entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")
        if not eid:
            return None

        doi = entry.get("prism:doi")
        title = entry.get("dc:title")
        if title and title.lower().startswith("[no title"):
            title = None

        authors = self._parse_authors(entry.get("author", []))
        if not authors:
            # Search API 默认只返回 first author，兜底构造
            creator = entry.get("dc:creator")
            if creator:
                authors = [{"given": "", "family": creator, "full_name": creator}]

        journal = entry.get("prism:publicationName")
        volume = entry.get("prism:volume")
        issue = entry.get("prism:issueIdentifier")
        page = entry.get("prism:pageRange")
        issn = entry.get("prism:issn") or entry.get("prism:eIssn")

        cover_date = entry.get("prism:coverDate")
        published_date = self._format_date(cover_date)

        article_type = entry.get("subtypeDescription") or entry.get("subtype")
        aggregation_type = entry.get("prism:aggregationType")

        citedby = entry.get("citedby-count")
        is_oa = entry.get("openaccessFlag")
        oa_category = "gold" if is_oa else None

        return {
            "DOI": doi,
            "source": "scopus",
            "title": title,
            "author": authors,
            "publisher": None,
            "published_date": published_date,
            "abstract": None,  # Search API 不返回摘要，需二次 enrichment
            "journal": journal,
            "journal_abbr": None,
            "volume": volume,
            "issue": issue,
            "page": page,
            "issn": issn,
            "article_type": article_type,
            "subject": None,
            "keywords": None,
            "oa_url": None,
            "oa_category": oa_category,
            "citation_count": self._to_int(citedby),
            "wos_times_cited": None,
            "references_count": None,
            "language": None,
            "external_ids": {"scopus_eid": eid},
            "meta_json": entry,
        }

    def fetch_abstract(self, eid: str) -> Optional[str]:
        """通过 Scopus Abstract Retrieval API 获取单条摘要。"""
        url = f"{self.ABSTRACT_URL}{eid}"
        resp = self._request(url, {})
        data = resp.json()
        retrieval = data.get("abstracts-retrieval-response", {})
        item = retrieval.get("item", {})
        br = item.get("bibrecord", {})
        head = br.get("head", {})
        abstract = head.get("abstracts")
        if not abstract:
            return None
        # 去除开头的版权符号前缀，如 "© 2025 AuthorName Purpose – ..."
        abstract = str(abstract).strip()
        if abstract.startswith("©"):
            abstract = abstract.split(" ", 2)[-1].strip()
        return abstract

    def _parse_authors(self, author_list):
        if isinstance(author_list, dict):
            author_list = [author_list]
        if not isinstance(author_list, list):
            return []
        authors = []
        for a in author_list:
            if not isinstance(a, dict):
                continue
            given = a.get("given-name") or a.get("given") or ""
            family = a.get("surname") or a.get("family") or ""
            full = a.get("authname") or f"{given} {family}".strip()
            if not full and family:
                full = family
            authors.append({
                "given": given,
                "family": family,
                "full_name": full,
                "orcid": normalize_orcid(a.get("orcid")),
                "affiliation": self._parse_affiliations(a.get("affiliation", [])),
            })
        return authors

    @staticmethod
    def _parse_affiliations(affiliation_data):
        if isinstance(affiliation_data, dict):
            affiliation_data = [affiliation_data]
        if not isinstance(affiliation_data, list):
            return []
        result = []
        for aff in affiliation_data:
            if isinstance(aff, dict):
                name = aff.get("affilname") or aff.get("name")
                if name:
                    result.append(name)
            elif isinstance(aff, str):
                result.append(aff)
        return result

    @staticmethod
    def _format_date(cover_date: Optional[str]) -> Optional[str]:
        """将 YYYY-MM-DD 或 YYYY-MM 转为标准日期。"""
        if not cover_date:
            return None
        parts = cover_date.split("-")
        try:
            y = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 1
            d = int(parts[2]) if len(parts) > 2 else 1
            return f"{y:04d}-{m:02d}-{d:02d}"
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _to_int(value):
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
