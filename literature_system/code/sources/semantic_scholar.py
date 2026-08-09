"""
Semantic Scholar 数据源适配器
API 文档: https://api.semanticscholar.org
AI2 开发的学术搜索引擎
"""
import os
import json
from typing import Dict, List
from .base import SourceAdapter

try:
    from ..logger import get_logger
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logger import get_logger

LOGGER = get_logger("semantic_scholar")

try:
    from .. import config
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

# Semantic Scholar Article Type 标准化映射
SEMANTIC_SCHOLAR_TYPE_MAPPING = {
    "JournalArticle": "Journal Article",
    "ConferencePaper": "Conference Paper",
    "Book": "Book",
    "BookChapter": "Book Chapter",
    "Dataset": "Dataset",
    "Repository": "Dataset",
    "Preprint": "Preprint",
    "Review": "Review",
    "Editorial": "Editorial",
    "CaseReport": "Case Report",
    "ClinicalTrial": "Clinical Trial",
    "News": "News",
    "MetaAnalysis": "Meta-Analysis",
    "Letter": "Letter",
    "Abstract": "Abstract",
    "Award": "Award",
    "Patent": "Patent",
    "Report": "Report",
    "Chapter": "Book Chapter",
    "Dataset": "Dataset",
    "Proceeding": "Conference Paper",
    "Snippet": "Other",
    "Thesis": "Dissertation",
}


class SemanticScholarAdapter(SourceAdapter):
    name = "semanticscholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def _get_headers(self):
        """获取请求头，包含 API Key 和 User-Agent"""
        headers = {
            "Accept": "application/json",
            "User-Agent": "LiteratureSystem/1.0 (contact: research@example.com; Academic Literature Collection)",
        }
        # 优先使用 config.py 中的配置
        api_key = config.SEMANTIC_SCHOLAR_API_KEY or os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
            print(f"    使用 API Key: {api_key[:10]}...")
        else:
            print("    ⚠️ 未设置 API Key，速率限制为 100次/5分钟")
        return headers

    def fetch(self, keyword: str, page: int = 0, page_size: int = 50, start_date: str = None, end_date: str = None):
        """
        从 Semantic Scholar 获取数据
        page: 页码（从 0 开始）
        page_size: 每页条数（最大 100）
        start_date: 开始日期 (YYYY-MM-DD)，仅支持年份过滤
        end_date: 结束日期 (YYYY-MM-DD)，仅支持年份过滤
        """
        page_size = min(page_size, 100)  # Semantic Scholar 最大 100
        offset = page * page_size

        headers = self._get_headers()

        params = {
            "query": keyword,
            "offset": offset,
            "limit": page_size,
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds,openAccessPdf,publicationTypes,journal"
        }
        
        # Semantic Scholar 支持 yearRange 过滤
        if start_date or end_date:
            start_year = start_date[:4] if start_date else "1900"
            end_year = end_date[:4] if end_date else "2100"
            params["yearRange"] = f"{start_year}-{end_year}"

        try:
            resp = self.request_with_retry(self.BASE_URL, params, headers=headers, timeout=30)
            data = resp.json()

            items = []
            for paper in data.get("data", []):
                external_ids = paper.get("externalIds", {})
                doi = external_ids.get("DOI")

                # 解析作者
                authors_list = paper.get("authors", [])
                authors = []
                for author in authors_list:
                    name = author.get("name", "")
                    if name:
                        parts = name.rsplit(" ", 1)
                        given = parts[0] if len(parts) > 1 else ""
                        family = parts[-1] if parts else name
                    else:
                        given = ""
                        family = ""
                    authors.append({
                        "given": given,
                        "family": family
                    })

                # 期刊信息
                venue = paper.get("venue")  # 会议或期刊名称
                journal_info = paper.get("journal", {}) or {}
                journal = journal_info.get("name") if isinstance(journal_info, dict) else venue
                journal_abbr = None

                # 出版年份
                year = paper.get("year")
                published_date = f"{year}-01-01" if year else None

                # 出版类型（标准化映射）
                pub_types = paper.get("publicationTypes", [])
                if pub_types:
                    standardized_types = []
                    for pt in pub_types:
                        standardized_types.append(SEMANTIC_SCHOLAR_TYPE_MAPPING.get(pt, pt))
                    article_type = "; ".join(standardized_types)
                else:
                    article_type = None

                # OA 信息
                oa_pdf = paper.get("openAccessPdf", {}) or {}
                oa_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None
                oa_category = "oa" if oa_url else None

                # 期刊详情
                volume = None
                issue = None
                page_str = None
                issn = None
                if isinstance(journal_info, dict):
                    volume = journal_info.get("volume")
                    issue = journal_info.get("issue")
                    page_str = journal_info.get("pages")
                    issn = journal_info.get("issn")

                item = {
                    "DOI": doi,
                    "source": self.name,
                    "title": paper.get("title"),
                    "author": json.dumps(authors, ensure_ascii=False),
                    "publisher": None,  # Semantic Scholar 不直接提供 publisher
                    "published_date": published_date,
                    "abstract": paper.get("abstract"),
                    "journal": journal,
                    "journal_abbr": journal_abbr,
                    "volume": volume,
                    "issue": issue,
                    "page": page_str,
                    "issn": issn,
                    "article_type": article_type,
                    "subject": None,  # Semantic Scholar 不提供详细分类
                    "oa_url": oa_url,
                    "oa_category": oa_category,
                    "citation_count": paper.get("citationCount"),
                    "language": None,
                    "external_ids": external_ids,
                    "meta_json": json.dumps({
                        "semantic_id": paper.get("paperId"),
                        "citation_count": paper.get("citationCount"),
                        "external_ids": external_ids,
                        "venue": venue,
                    }, ensure_ascii=False)
                }
                items.append(item)

            return items

        except Exception as e:
            print(f"Semantic Scholar 请求失败: {e}")
            return []

    def fetch_by_doi(self, doi: str):
        """
        通过 DOI 获取单条文献信息（用于作者补全）
        方案 C: 作为 Crossref 的 fallback 兜底
        """
        if not doi:
            return None

        headers = self._get_headers()
        # 使用 DOI 直接查询 API
        url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}"
        params = {
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds,openAccessPdf"
        }

        try:
            resp = self.request_with_retry(url, params, headers=headers, timeout=30)
            paper = resp.json()

            if not paper.get("title"):
                return None

            # 解析作者为字符串
            authors_list = paper.get("authors", [])
            authors_str = ", ".join([
                author.get("name", "")
                for author in authors_list
                if author.get("name")
            ])

            return {
                "doi": doi,
                "title": paper.get("title"),
                "author": authors_str,
                "year": paper.get("year"),
                "abstract": paper.get("abstract"),
                "venue": paper.get("venue"),
            }
        except Exception as e:
            print(f"Semantic Scholar DOI 查询失败 ({doi}): {e}")
            return None

    def fetch_by_dois_batch(self, dois: List[str], batch_size: int = 100) -> Dict[str, Dict]:
        """通过 DOI 列表批量获取文献信息（用于作者补全）。

        Semantic Scholar /paper/batch 端点一次最多支持 100 个 ID。
        返回: {doi_lower: {doi, title, author, year, abstract, venue}}
        """
        if not dois:
            return {}

        results: Dict[str, Dict] = {}
        headers = self._get_headers()
        url = "https://api.semanticscholar.org/graph/v1/paper/batch"
        params = {
            "fields": "title,authors.authorId,authors.name,year,venue,abstract,citationCount,externalIds,openAccessPdf,fieldsOfStudy"
        }

        for i in range(0, len(dois), batch_size):
            batch = dois[i : i + batch_size]
            ids = [f"DOI:{d}" for d in batch if d]
            if not ids:
                continue

            try:
                resp = self.request_with_retry(
                    url,
                    params=params,
                    headers=headers,
                    method="POST",
                    json={"ids": ids},
                    timeout=60,
                )
                papers = resp.json()
                if not isinstance(papers, list):
                    LOGGER.warning("Semantic Scholar batch 返回非列表: %s", type(papers))
                    continue

                for paper in papers:
                    if not paper:
                        continue
                    external_ids = paper.get("externalIds", {}) or {}
                    doi = external_ids.get("DOI")
                    if not doi:
                        # 尝试从 paperId 解析，如 "DOI:10.xxx"
                        paper_id = paper.get("paperId", "")
                        if paper_id.startswith("DOI:"):
                            doi = paper_id[4:]
                    if not doi:
                        continue

                    authors_list = paper.get("authors", [])
                    authors_str = ", ".join([
                        author.get("name", "")
                        for author in authors_list
                        if author.get("name")
                    ])

                    results[doi.lower()] = {
                        "doi": doi,
                        "title": paper.get("title"),
                        "author": authors_str,
                        "authors": paper.get("authors") or [],
                        "year": paper.get("year"),
                        "abstract": paper.get("abstract"),
                        "venue": paper.get("venue"),
                        "citation_count": paper.get("citationCount"),
                        "fields_of_study": paper.get("fieldsOfStudy") or [],
                    }
            except Exception as e:
                LOGGER.warning("Semantic Scholar 批量查询失败 (batch %d-%d): %s", i, i + len(batch), e)

        return results
