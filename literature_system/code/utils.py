import html
import json
import re
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# ORCID 标准化
# ---------------------------------------------------------------------------

_ORCID_RE = re.compile(r"^\s*(https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\s*$", re.IGNORECASE)


def normalize_orcid(value) -> Optional[str]:
    """
    清洗并校验 ORCID。
    支持带 https://orcid.org/ 前缀、大小写、多余空格等变体。
    返回标准 16 位 ORCID 字符串，无效时返回 None。
    """
    if not value:
        return None
    value = str(value).strip()
    if value.lower() in ("none", "null", "nan", ""):
        return None
    m = _ORCID_RE.match(value)
    if not m:
        return None
    return m.group(2).upper()


# ---------------------------------------------------------------------------
# 期刊分级查询（惰性加载）
# ---------------------------------------------------------------------------

_JOURNAL_TIER_MAP = None


def _load_journal_tiers():
    """加载期刊分级配置，返回 {normalized_name: tier} 字典。"""
    global _JOURNAL_TIER_MAP
    if _JOURNAL_TIER_MAP is not None:
        return _JOURNAL_TIER_MAP

    root = Path(__file__).resolve().parents[1]
    config_path = root / "config" / "journal_tiers.json"
    tiers = {"tier1": [], "tier2": [], "tier3": []}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            for tier in ("tier1", "tier2", "tier3"):
                tiers[tier] = data.get(tier, [])
        except (json.JSONDecodeError, OSError):
            pass

    def _normalize(name):
        if not name:
            return ""
        name = name.strip().lower()
        # 统一 & 与 and 两种写法，便于匹配
        return name.replace("&", " and ").replace(",", " ").replace("  ", " ").strip()

    mapping = {}
    for tier, names in tiers.items():
        for name in names:
            mapping[_normalize(name)] = tier
    _JOURNAL_TIER_MAP = mapping
    return _JOURNAL_TIER_MAP


def get_journal_tier(journal_name):
    """
    根据期刊名返回分级：tier1 / tier2 / tier3 / other
    支持大小写不敏感、&/and 变体匹配。
    """
    if not journal_name:
        return "other"
    normalized = (
        journal_name.strip()
        .lower()
        .replace("&", " and ")
        .replace(",", " ")
        .replace("  ", " ")
        .strip()
    )
    return _load_journal_tiers().get(normalized, "other")


def parse_authors(author_list):
    """解析作者列表，返回结构化信息（含标准化 ORCID）"""
    authors = []
    for a in author_list or []:
        authors.append({
            "orcid": normalize_orcid(a.get("ORCID")),
            "given": a.get("given"),
            "family": a.get("family"),
            "affiliation": normalize_affiliations(a.get("affiliation", [])),
        })
    return authors


def parse_funders(funder_list):
    """解析资助信息"""
    funders = []
    for f in funder_list or []:
        funders.append({
            "doi": f.get("DOI"),
            "name": f.get("name"),
            "award": f.get("award"),
            "award_info": f.get("award-info"),
        })
    return funders


def parse_licenses(license_list):
    """解析许可信息"""
    licenses = []
    for l in license_list or []:
        licenses.append({
            "url": l.get("URL"),
            "content_version": l.get("content-version"),
            "start_date": (l.get("start") or {}).get("date-time"),
        })
    return licenses


def parse_relations(relation_dict):
    """解析relation字段"""
    relations = []
    for rel_type, rel_items in (relation_dict or {}).items():
        for item in rel_items or []:
            relations.append({
                "type": rel_type,
                "id": item.get("id"),
                "id_type": item.get("id-type"),
                "asserted_by": item.get("asserted-by"),
            })
    return relations


def parse_links(link_list):
    """解析link字段"""
    links = []
    for l in link_list or []:
        links.append({
            "url": l.get("URL"),
            "content_type": l.get("content-type"),
            "content_version": l.get("content-version"),
            "intended_application": l.get("intended-application"),
        })
    return links


def clean_abstract(raw_abstract):
    """清洗HTML摘要"""
    if not raw_abstract:
        return None
    text = html.unescape(raw_abstract)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_affiliations(affiliations):
    """作者机构标准化"""
    normalized = []
    for aff in affiliations or []:
        if isinstance(aff, dict):
            name = aff.get("name")
        else:
            name = str(aff)
        if name:
            cleaned = re.sub(r"\s+", " ", name).strip()
            normalized.append(cleaned)
    return list(dict.fromkeys(normalized))


def parse_published_date(item):
    """解析日期并返回ISO格式字符串"""
    date_fields = ["published-print", "published-online", "issued", "created"]
    for field in date_fields:
        parts = (item.get(field) or {}).get("date-parts")
        if parts and parts[0]:
            raw = parts[0]
            if not isinstance(raw, (list, tuple)):
                continue
            ymd = list(raw) + [1] * (3 - len(raw))
            if any(v is None for v in ymd[:3]):
                return None
            try:
                return date(int(ymd[0]), int(ymd[1]), int(ymd[2])).isoformat()
            except (ValueError, TypeError):
                return None
    return None


def normalize_crossref_item(item):
    """
    将 Crossref 原始数据标准化为统一字段格式
    
    提取:
    - doi: DOI 标识符
    - title: 论文标题
    - author: 作者列表
    - published_date: 发布日期
    - abstract: 摘要
    - publisher: 出版社
    - journal: 期刊名称
    - volume/issue/page: 卷期页
    - issn: ISSN
    - article_type: 文章类型
    - external_ids: 从 alternative-id 提取
    - oa_category: 从 license 的 content-version 判断 OA 类型
    - oa_url: 从 link 提取 PDF 链接
    """
    # 提取核心字段
    normalized = {
        'source': 'crossref',
        'doi': item.get('DOI', ''),
        'title': _get_title(item),
        'author': _get_author(item),
        'published_date': _get_date(item),
        'abstract': _get_abstract(item),
        'publisher': item.get('publisher', ''),
        'journal': _get_journal(item),
        'volume': item.get('volume', ''),
        'issue': item.get('issue', ''),
        'page': item.get('page', ''),
        'issn': _get_issn(item),
        'article_type': item.get('type', ''),
        'language': item.get('language'),
        'subject': item.get('subject', []),
        'keywords': item.get('subject', []),
        'citation_count': item.get('is-referenced-by-count'),
        'references_count': item.get('reference-count'),
    }
    
    # 1. external_ids: 从 alternative-id 提取
    alt_ids = item.get("alternative-id", [])
    if alt_ids:
        external_ids = {}
        for alt_id in alt_ids:
            alt_str = str(alt_id)
            if alt_str.startswith("10."):
                continue  # DOI 跳过
            elif alt_str.startswith("arXiv:"):
                external_ids["arxiv_id"] = alt_str
            elif alt_str.startswith("PMC"):
                external_ids["pmc_id"] = alt_str
            elif alt_str.startswith("PMID:"):
                external_ids["pmid"] = alt_str.replace("PMID:", "")
            elif alt_str.startswith("ISBN"):
                external_ids["isbn"] = alt_str
            else:
                if "PMC" in alt_str:
                    external_ids["pmc_id"] = alt_str
                elif "arxiv" in alt_str.lower():
                    external_ids["arxiv_id"] = alt_str
        normalized["external_ids"] = external_ids if external_ids else None
    else:
        normalized["external_ids"] = None
    
    # 2. oa_category: 从 license 的 content-version 判断
    licenses = item.get("license", [])
    oa_category = None
    for lic in licenses or []:
        content_version = lic.get("content-version", "").lower()
        if content_version in ("vor", "published"):
            oa_category = "publisher-gold"
            break
        elif content_version == "tdm":
            oa_category = "tdm"
            break
    if oa_category:
        normalized["oa_category"] = oa_category
    elif item.get("is-open-access"):
        normalized["oa_category"] = "open-access"
    else:
        normalized["oa_category"] = None
    
    # 3. oa_url: 从 link 提取 PDF 链接
    links = item.get("link", [])
    oa_url = None
    for link in links or []:
        content_type = link.get("content-type", "")
        intended_app = link.get("intended-application", "")
        url = link.get("URL", "")
        if "pdf" in content_type.lower() or "pdf" in intended_app.lower():
            oa_url = url
            break
        elif "xml" in content_type.lower() or "text/xml" in content_type.lower():
            if not oa_url:
                oa_url = url
    normalized["oa_url"] = oa_url
    
    return normalized


def _get_title(item):
    """提取标题"""
    title = item.get('title')
    if isinstance(title, list):
        return title[0] if title else ''
    return title or ''


def _get_author(item):
    """提取作者列表"""
    authors = item.get('author', [])
    if not authors:
        return ''
    author_list = []
    for a in authors:
        given = a.get('given', '')
        family = a.get('family', '')
        if given and family:
            author_list.append(f"{given} {family}")
        elif family:
            author_list.append(family)
    return ', '.join(author_list)


def _get_date(item):
    """提取发布日期"""
    issued = item.get('issued', {})
    date_parts = issued.get('date-parts', [])
    if date_parts and date_parts[0]:
        parts = date_parts[0]
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]:02d}-{parts[2]:02d}"
        elif len(parts) >= 2:
            return f"{parts[0]}-{parts[1]:02d}-01"
        elif len(parts) >= 1:
            return f"{parts[0]}-01-01"
    return ''


def _get_abstract(item):
    """提取摘要"""
    abstract = item.get('abstract', '')
    if not abstract:
        return ''
    # 去除 HTML 标签
    import re
    abstract = re.sub(r'<[^>]+>', '', abstract)
    return abstract.strip()


def _get_journal(item):
    """提取期刊名称"""
    container = item.get('container-title', [])
    if isinstance(container, list):
        return container[0] if container else ''
    return container or ''


def _get_issn(item):
    """提取 ISSN"""
    issn_list = item.get('ISSN', [])
    if isinstance(issn_list, list):
        return issn_list[0] if issn_list else ''
    return issn_list or ''
