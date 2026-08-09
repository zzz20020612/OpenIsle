"""
Web of Science (Clarivate) 数据源适配器

说明：
- WOS API 为机构订阅 API，需要 Clarivate 颁发的 API Key。
- 当前实现基于 WOS Expanded API v3 常见字段结构；
  若实际返回结构不同，请调整 _parse_record 中的 JSON Path。
- 支持 WOS 高级检索式（TS/SO/PY 等）和关键词检索。
"""
import os
import time
from typing import List, Optional

from .base import SourceAdapter

try:
    from .. import config
    from ..utils import normalize_orcid
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    from utils import normalize_orcid


class WosAdapter(SourceAdapter):
    name = "wos"
    DATABASE_ID = "WOS"

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": config.WOS_USER_AGENT,
        }
        api_key = config.WOS_API_KEY
        if api_key:
            headers["X-ApiKey"] = api_key
        return headers

    def _build_query(
        self,
        keyword: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        构造 WOS 高级检索式。
        如果 keyword 已包含 TS=/SO= 等字段，则原样使用；否则包装为 TS=keyword。
        """
        query = keyword.strip()
        if not any(query.upper().startswith(prefix) for prefix in ("TS=", "SO=", "PY=", "DO=", "AU=")):
            query = f'TS=({query})'

        date_parts = []
        if start_date:
            date_parts.append(f"PY>={start_date[:4]}")
        if end_date:
            date_parts.append(f"PY<={end_date[:4]}")
        if date_parts:
            query = f"{query} AND {' AND '.join(date_parts)}"
        return query

    def fetch(
        self,
        keyword: str,
        page: int = 0,
        page_size: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """
        从 WOS API 检索文献。

        Args:
            keyword: 检索词或 WOS 高级检索式
            page: 页码（从 0 开始）
            page_size: 每页条数（WOS 通常最大 100）
            start_date/end_date: 日期过滤，取年份部分
        """
        if not config.WOS_API_KEY:
            raise RuntimeError("未配置 WOS_API_KEY，无法调用 Web of Science API")

        page_size = min(page_size, 100)
        first_record = page * page_size + 1

        query = self._build_query(keyword, start_date, end_date)
        params = {
            "databaseId": self.DATABASE_ID,
            "usrQuery": query,
            "count": page_size,
            "firstRecord": first_record,
        }

        headers = self._get_headers()
        resp = self.request_with_retry(
            config.WOS_API_URL, params, headers=headers, timeout=60
        )
        data = resp.json()

        records = []
        raw_records = []
        # WOS API 常见返回结构：Data.Records.Record（列表）
        data_section = data.get("Data") or {}
        records_section = data_section.get("Records") or {}
        if isinstance(records_section, dict):
            raw_records = records_section.get("Record") or []
        elif isinstance(records_section, list):
            raw_records = records_section

        if isinstance(raw_records, dict):
            # 单条记录时 API 可能返回对象而非列表
            raw_records = [raw_records]

        for record in raw_records:
            parsed = self._parse_record(record)
            if parsed:
                records.append(parsed)

        time.sleep(config.WOS_SLEEP_BETWEEN)
        return records

    def _parse_record(self, record: dict) -> Optional[dict]:
        """将 WOS API 单条记录解析为项目统一字段。"""
        # 字段路径根据实际 API 响应可能需要调整
        uid = record.get("UID") or record.get("ut")
        if not uid:
            return None

        static_data = record.get("static_data", {}) or {}
        summary = static_data.get("summary", {}) or {}
        titles = summary.get("titles", {}) or {}
        title_list = titles.get("title", [])
        title = self._pick_title(title_list)

        names = static_data.get("summary", {}).get("names", {}) or {}
        author_list = names.get("name", [])
        authors = self._parse_authors(author_list)

        doctypes = summary.get("doctypes", {}) or {}
        doctype_list = doctypes.get("doctype", [])
        article_type = doctype_list[0] if isinstance(doctype_list, list) and doctype_list else "Journal Article"

        pub_info = summary.get("pub_info", {}) or {}
        published_date = self._parse_date(pub_info)

        # 期刊信息
        journal = self._pick_journal(title_list)
        journal_abbr = self._pick_journal_abbr(title_list)
        volume = pub_info.get("vol") or pub_info.get("volume")
        issue = pub_info.get("issue")
        page = pub_info.get("page", {}).get("begin") or pub_info.get("page", {}).get("content")

        # ISSN
        identifiers = static_data.get("summary", {}).get("identifiers", {}) or {}
        issn = self._pick_identifier(identifiers, "issn")
        doi = self._pick_identifier(identifiers, "doi")

        # 关键词
        fullrecord_metadata = static_data.get("fullrecord_metadata", {}) or {}
        keywords_data = fullrecord_metadata.get("keywords", {}) or {}
        keywords = self._parse_keywords(keywords_data.get("keyword", []))

        # 被引次数
        citation_counts = record.get("dynamic_data", {}).get("citation_related", {}).get("citation_counts", {}) or {}
        wos_times_cited = citation_counts.get("wos_citation_count") or citation_counts.get("count")

        # 摘要（WOS API 完整摘要通常需要额外 subscription，此处优先取 summary 中的）
        abstract = self._parse_abstract(static_data)

        return {
            "DOI": doi,
            "wos_id": uid,
            "source": "wos",
            "title": title,
            "author": authors,
            "publisher": None,
            "published_date": published_date,
            "abstract": abstract,
            "journal": journal,
            "journal_abbr": journal_abbr,
            "volume": volume,
            "issue": issue,
            "page": page,
            "issn": issn,
            "article_type": article_type,
            "subject": None,
            "keywords": keywords,
            "oa_url": None,
            "oa_category": None,
            "citation_count": None,
            "wos_times_cited": self._to_int(wos_times_cited),
            "references_count": None,
            "language": None,
            "external_ids": {"wos_id": uid},
            "meta_json": record,
        }

    @staticmethod
    def _pick_title(title_list):
        if isinstance(title_list, dict):
            title_list = [title_list]
        if not isinstance(title_list, list):
            return None
        for t in title_list:
            if isinstance(t, dict) and t.get("type") == "item":
                return t.get("content")
        for t in title_list:
            if isinstance(t, dict) and t.get("type") == "source":
                return t.get("content")
        return title_list[0].get("content") if title_list else None

    @staticmethod
    def _pick_journal(title_list):
        if isinstance(title_list, dict):
            title_list = [title_list]
        if not isinstance(title_list, list):
            return None
        for t in title_list:
            if isinstance(t, dict) and t.get("type") == "source":
                return t.get("content")
        return None

    @staticmethod
    def _pick_journal_abbr(title_list):
        if isinstance(title_list, dict):
            title_list = [title_list]
        if not isinstance(title_list, list):
            return None
        for t in title_list:
            if isinstance(t, dict) and t.get("type") == "abbrev_iso":
                return t.get("content")
        return None

    @staticmethod
    def _parse_authors(author_list):
        if isinstance(author_list, dict):
            author_list = [author_list]
        if not isinstance(author_list, list):
            return []
        authors = []
        for a in author_list:
            if not isinstance(a, dict):
                continue
            given = a.get("first_name") or a.get("given") or ""
            family = a.get("last_name") or a.get("family") or a.get("surname") or ""
            full = a.get("full_name") or a.get("display_name") or ""
            if not full and (given or family):
                full = f"{given} {family}".strip()
            authors.append({
                "given": given,
                "family": family,
                "full_name": full,
                "orcid": normalize_orcid(a.get("orcid")),
                "affiliation": a.get("affiliation", []),
            })
        return authors

    @staticmethod
    def _parse_keywords(keywords):
        if isinstance(keywords, str):
            return [keywords]
        if isinstance(keywords, dict):
            return [keywords.get("content")] if keywords.get("content") else []
        if isinstance(keywords, list):
            result = []
            for k in keywords:
                if isinstance(k, str):
                    result.append(k)
                elif isinstance(k, dict):
                    result.append(k.get("content"))
            return [k for k in result if k]
        return []

    @staticmethod
    def _pick_identifier(identifiers, id_type: str):
        if not isinstance(identifiers, dict):
            return None
        items = identifiers.get("identifier", [])
        if isinstance(items, dict):
            items = [items]
        for item in items or []:
            if isinstance(item, dict) and item.get("type", "").lower() == id_type:
                return item.get("value") or item.get("content")
        return None

    @staticmethod
    def _parse_date(pub_info):
        year = pub_info.get("pubyear") or pub_info.get("year") or pub_info.get("pub_year")
        month = pub_info.get("pubmonth") or pub_info.get("month")
        day = pub_info.get("pubday") or pub_info.get("day")
        if not year:
            return None
        try:
            y = int(year)
            m = int(month) if month else 1
            d = int(day) if day else 1
            return f"{y:04d}-{m:02d}-{d:02d}"
        except (ValueError, TypeError):
            return f"{year}-01-01"

    @staticmethod
    def _parse_abstract(static_data):
        abstract_data = static_data.get("fullrecord_metadata", {}).get("abstracts", {}).get("abstract", {}) or {}
        if isinstance(abstract_data, dict):
            return abstract_data.get("content") or abstract_data.get("p")
        if isinstance(abstract_data, list) and abstract_data:
            return abstract_data[0].get("content") if isinstance(abstract_data[0], dict) else str(abstract_data[0])
        return None

    @staticmethod
    def _to_int(value):
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
