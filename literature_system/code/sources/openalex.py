"""
OpenAlex 数据源适配器
API 文档: https://docs.openalex.org
覆盖几乎所有主要出版社的商业期刊
"""
import json
from urllib.parse import urlencode
from .base import SourceAdapter


class OpenAlexAdapter(SourceAdapter):
    name = "openalex"
    BASE_URL = "https://api.openalex.org/works"

    def fetch(self, keyword: str, page: int = 0, page_size: int = 50, start_date: str = None, end_date: str = None):
        """
        从 OpenAlex 获取数据
        page: 页码（OpenAlex 使用 cursor 分页）
        page_size: 每页条数（最大 200）
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        """
        page_size = min(page_size, 200)  # OpenAlex 最大 200

        params = {
            "search": keyword,
            "per_page": page_size,
            "mailto": "research@example.com",  # 礼貌标识
        }
        
        # OpenAlex 日期过滤
        if start_date:
            params["from_publication_date"] = start_date
        if end_date:
            params["to_publication_date"] = end_date

        # OpenAlex 使用 cursor 分页
        cursor = page
        if page > 0:
            # 初始请求会返回 next_cursor
            pass

        try:
            resp = self.request_with_retry(self.BASE_URL, params, timeout=30)
            data = resp.json()

            items = []
            for work in data.get("results", []):
                # 解析 DOI
                doi = work.get("doi")
                if doi:
                    doi = doi.replace("https://doi.org/", "")

                # 解析作者
                authorships = work.get("authorships", [])
                authors = []
                for auth in authorships:
                    author = auth.get("author", {})
                    display_name = author.get("display_name", "")
                    if display_name:
                        parts = display_name.rsplit(" ", 1)
                        given = parts[0] if len(parts) > 1 else ""
                        family = parts[-1] if parts else display_name
                    else:
                        given = ""
                        family = ""
                    authors.append({
                        "given": given,
                        "family": family,
                        "orcid": auth.get("author", {}).get("orcid"),
                        "affiliation": "; ".join([
                            inst.get("display_name", "")
                            for inst in auth.get("institutions", [])
                            if inst.get("display_name")
                        ])
                    })

                # 解析期刊信息
                primary_location = work.get("primary_location", {})
                source = primary_location.get("source", {})
                journal = source.get("display_name") if source else None
                journal_abbr = source.get("host_organization_name") if source else None
                issn = source.get("issn", [None])[0] if source and source.get("issn") else None

                # 解析出版信息
                publication_date = work.get("publication_date")
                publisher = work.get("publisher")

                # 解析期刊详情
                volume = primary_location.get("biblio", {}).get("volume") if primary_location else None
                issue = primary_location.get("biblio", {}).get("issue") if primary_location else None
                first_page = primary_location.get("biblio", {}).get("first_page") if primary_location else None
                last_page = primary_location.get("biblio", {}).get("last_page") if primary_location else None
                page_str = f"{first_page}-{last_page}" if first_page and last_page else first_page

                # 解析类型
                doc_type = work.get("type")  # work type 如 article, book, etc.

                # 解析主题
                topics = work.get("topics", [])
                subjects = [t.get("display_name") for t in topics[:5] if t.get("display_name")]

                # OpenAlex 没有专门的 oa_url，需要检查 best_oa_location
                best_oa = work.get("best_oa_location", {})
                oa_url = best_oa.get("url") if best_oa else None
                oa_category = "oa" if oa_url else None

                # 摘要（OpenAlex 有时会提供）
                abstract_inverted_index = work.get("abstract_inverted_index")
                abstract = None
                if abstract_inverted_index:
                    # 重建摘要文本
                    words = []
                    for word, positions in abstract_inverted_index.items():
                        for pos in positions:
                            words.append((pos, word))
                    words.sort(key=lambda x: x[0])
                    abstract = " ".join([w[1] for w in words])

                item = {
                    "DOI": doi,
                    "source": self.name,
                    "title": work.get("display_name"),
                    "author": json.dumps(authors, ensure_ascii=False),
                    "publisher": publisher,
                    "published_date": publication_date,
                    "abstract": abstract,
                    "journal": journal,
                    "journal_abbr": journal_abbr,
                    "volume": volume,
                    "issue": issue,
                    "page": page_str,
                    "issn": issn,
                    "article_type": doc_type,
                    "subject": json.dumps(subjects, ensure_ascii=False) if subjects else None,
                    "oa_url": oa_url,
                    "oa_category": oa_category,
                    "citation_count": work.get("cited_by_count"),
                    "language": work.get("language"),
                    "external_ids": {
                        "openalex_id": work.get("id"),
                    },
                    "meta_json": json.dumps({
                        "openalex_id": work.get("id"),
                        "cited_by_count": work.get("cited_by_count"),
                        "publication_year": work.get("publication_year"),
                        "language": work.get("language"),
                        "doi": work.get("doi"),
                    }, ensure_ascii=False)
                }
                items.append(item)

            return items

        except Exception as e:
            print(f"OpenAlex 请求失败: {e}")
            return []
