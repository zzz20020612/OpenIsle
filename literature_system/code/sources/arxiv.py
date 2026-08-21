import xml.etree.ElementTree as ET
import json
from .base import SourceAdapter


class ArxivAdapter(SourceAdapter):
    name = "arxiv"

    def fetch(self, keyword: str, page: int, page_size: int, start_date: str = None, end_date: str = None):
        # arXiv 日期过滤格式: from_date:YYYY-MM-DD and to_date:YYYY-MM-DD
        date_filter = ""
        if start_date:
            date_filter += f" AND from_date:{start_date}"
        if end_date:
            date_filter += f" AND to_date:{end_date}"
        
        params = {
            "search_query": f"all:{keyword}{date_filter}",
            "start": page * page_size,
            "max_results": page_size,
        }
        # HTTPS is materially more reliable from the Docker network.  The HTTP
        # endpoint can leave a workflow worker waiting through every retry even
        # though the same query succeeds immediately over TLS.
        resp = self.request_with_retry(
            "https://export.arxiv.org/api/query",
            params=params,
            timeout=15,
            max_retries=2,
        )
        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        items = []
        for entry in root.findall("atom:entry", ns):
            # 解析作者
            authors = []
            for author in entry.findall("atom:author", ns):
                given = author.findtext("atom:name", default="", namespaces=ns).split()[-1] if author.findtext("atom:name", default="", namespaces=ns) else ""
                family = author.findtext("atom:name", default="", namespaces=ns).split()[0] if author.findtext("atom:name", default="", namespaces=ns) else ""
                if family and family != given:
                    given = " ".join(author.findtext("atom:name", default="", namespaces=ns).split()[:-1])
                authors.append({"given": given, "family": family})

            # 解析分类
            categories = []
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term", "")
                if term:
                    categories.append(term)

            # arXiv ID 转 DOI（如果有）
            arxiv_id = entry.findtext("atom:id", default="", namespaces=ns)
            doi = entry.findtext("arxiv:doi", default="", namespaces=ns) if entry.find("arxiv:doi", ns) is not None else None

            # 优先从 atom:link 获取 PDF 直链
            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href")
                    break
            # 兜底：将 abs URL 替换为 pdf URL（使用 HTTPS，避免部分地区 HTTP 被重置）
            if not pdf_url and arxiv_id:
                pdf_url = arxiv_id.replace("http://", "https://").replace("/abs/", "/pdf/") + ".pdf"

            # arXiv 没有正式期刊信息，但有预印本信息
            item = {
                "DOI": doi,
                "source": "arxiv",
                "title": entry.findtext("atom:title", default="", namespaces=ns).strip().replace("\n", " "),
                "author": json.dumps(authors, ensure_ascii=False),
                "publisher": "arXiv",
                "published_date": entry.findtext("atom:published", default="", namespaces=ns)[:10] if entry.findtext("atom:published") else None,
                "abstract": entry.findtext("atom:summary", default="", namespaces=ns).strip().replace("\n", " "),
                # arXiv 特有
                "journal": "arXiv preprint",  # arXiv 作为预印本平台
                "journal_abbr": "arXiv",
                "article_type": "preprint",
                "subject": json.dumps(categories, ensure_ascii=False),
                "oa_url": pdf_url,
                "oa_category": "; ".join(categories[:5]) if categories else None,  # 取前5个分类
                # 原始数据
                "meta_json": json.dumps({
                    "id": arxiv_id,
                    "updated": entry.findtext("atom:updated"),
                    "title": entry.findtext("atom:title"),
                    "summary": entry.findtext("atom:summary"),
                    "published": entry.findtext("atom:published"),
                    "categories": categories,
                    "links": [{"url": link.get("href"), "type": link.get("type")} for link in entry.findall("atom:link", ns)]
                }, ensure_ascii=False)
            }
            items.append(item)
        return items
