"""
PubMed 数据源适配器
API 文档: https://www.ncbi.nlm.nih.gov/home/develop/api/
使用 E-utilities API
"""
import json
import time
import xml.etree.ElementTree as ET
from .base import SourceAdapter


class PubmedAdapter(SourceAdapter):
    name = "pubmed"
    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def _parse_date(self, pubdate):
        """解析 PubMed 日期"""
        if pubdate is None:
            return None
        year = pubdate.findtext("Year")
        month = pubdate.findtext("Month")
        day = pubdate.findtext("Day")
        if not year:
            return None
        month_map = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        if month and month.isdigit():
            month = month.zfill(2)
        elif month:
            month = month_map.get(month, "01")
        else:
            month = "01"
        day = day.zfill(2) if day and day.isdigit() else "01"
        return f"{year}-{month}-{day}"

    def _parse_article(self, article):
        """解析单篇文章"""
        # 解析 PMID
        pmid = article.findtext(".//PMID")

        # 解析 DOI
        article_ids = article.findall(".//ArticleId")
        doi = None
        pmc_id = None
        for aid in article_ids:
            idtype = aid.get("IdType")
            if idtype == "doi":
                doi = aid.text
            elif idtype == "pmc":
                pmc_id = aid.text

        # 解析标题
        title = article.findtext(".//ArticleTitle") or ""

        # 解析摘要
        abstract_elem = article.find(".//Abstract")
        abstracttext = ""
        if abstract_elem is not None:
            abstract_parts = []
            for ab in abstract_elem.findall("AbstractText"):
                label = ab.get("Label", "")
                text = ab.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstracttext = " ".join(abstract_parts)

        # 解析作者
        author_list = article.findall(".//Author")
        authors = []
        for author in author_list:
            last_name = author.findtext("LastName", "")
            fore_name = author.findtext("ForeName", "")
            affiliation = author.findtext("AffiliationInfo/Affiliation", "")
            orcid = None
            for ident in author.findall("Identifier"):
                if ident.get("Source", "").upper() == "ORCID":
                    orcid = ident.text
                    break
            if last_name or fore_name:
                authors.append({
                    "given": fore_name,
                    "family": last_name,
                    "orcid": orcid,
                    "affiliation": affiliation
                })

        # 解析期刊信息
        journal = article.find(".//Journal")
        journal_name = journal.findtext("Title", "") if journal is not None else None
        journal_abbr = journal.findtext("ISOAbbreviation", "") if journal is not None else None

        journal_issue = article.find(".//JournalIssue") if journal is not None else None
        volume = journal_issue.findtext("Volume") if journal_issue is not None else None
        issue = journal_issue.findtext("Issue") if journal_issue is not None else None

        pub_date_elem = journal_issue.find("PubDate") if journal_issue is not None else None
        pub_date = self._parse_date(pub_date_elem)

        # 解析页码
        pages = article.findtext(".//Pagination/MedlinePgn", "")

        # 解析 ISSN
        issn_elem = article.find(".//ISSN")
        issn = issn_elem.text if issn_elem is not None else None

        # 解析文章类型
        pubtype_list = article.findall(".//PublicationType")
        article_type = pubtype_list[0].text if pubtype_list else None

        # 解析关键词
        keyword_list = article.findall(".//Keyword")
        keywords = [k.text for k in keyword_list if k.text][:5]

        # OA URL
        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/" if pmc_id else None
        oa_category = "pmc_article" if pmc_id else None

        return {
            "DOI": doi,
            "source": self.name,
            "title": title,
            "author": json.dumps(authors, ensure_ascii=False),
            "publisher": "PubMed/NCBI",
            "published_date": pub_date,
            "abstract": abstracttext if abstracttext else None,
            "journal": journal_name,
            "journal_abbr": journal_abbr,
            "volume": volume,
            "issue": issue,
            "page": pages,
            "issn": issn,
            "article_type": article_type,
            "subject": json.dumps(keywords, ensure_ascii=False) if keywords else None,
            "oa_url": oa_url,
            "oa_category": oa_category,
            "citation_count": None,
            "language": None,
            "external_ids": {
                "pmid": pmid,
                "pmc_id": pmc_id,
            },
            "meta_json": json.dumps({
                "pmid": pmid,
                "pmc_id": pmc_id,
            }, ensure_ascii=False)
        }

    def fetch(self, keyword: str, page: int = 0, page_size: int = 50, start_date: str = None, end_date: str = None):
        """
        从 PubMed 获取数据
        page: 页码
        page_size: 每页条数（最大 1万）
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        """
        retstart = page * page_size

        # PubMed 日期过滤：在搜索词中添加日期范围
        date_filter = ""
        if start_date:
            date_filter = f" AND ({start_date}[dp] : {end_date or '3000'}[dp])" if end_date else f" AND ({start_date}[dp] : 3000[dp])"

        # Step 1: 搜索获取 ID 列表
        search_params = {
            "db": "pubmed",
            "term": keyword + date_filter,
            "retstart": retstart,
            "retmax": page_size,
            "retmode": "json",
            "sort": "relevance",
            "email": "research@example.com"
        }

        try:
            resp = self.request_with_retry(self.SEARCH_URL, search_params, timeout=30)
            search_data = resp.json()
            ids = search_data.get("esearchresult", {}).get("idlist", [])

            if not ids:
                return []

            # Step 2: 获取详情（使用 XML 格式便于解析）
            time.sleep(0.34)  # NCBI 要求每秒不超过 3 个请求

            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
                "rettype": "abstract",
                "email": "research@example.com"
            }

            resp = self.request_with_retry(self.FETCH_URL, fetch_params, timeout=60)
            root = ET.fromstring(resp.content)

            items = []
            for article in root.findall(".//PubmedArticle"):
                try:
                    parsed = self._parse_article(article)
                    items.append(parsed)
                except Exception as e:
                    print(f"解析文章失败: {e}")
                    continue

            return items

        except Exception as e:
            print(f"PubMed 请求失败: {e}")
            return []
