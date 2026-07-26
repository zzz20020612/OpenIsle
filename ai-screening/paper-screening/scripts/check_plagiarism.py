"""重复文本检测 — 聚合免费学术 API 查重。

用法: echo '<parsed-json>' | python check_plagiarism.py
输出: dim-02 维度结果 JSON

API 来源:
- Semantic Scholar (100次/5分钟)
- OpenAlex (无硬限制)
- Europe PMC (无硬限制)
- arXiv (3秒间隔)
- CrossRef (无硬限制)
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

_API_TIMEOUT = 10.0  # 秒
_SIMILARITY_THRESHOLD = 0.85  # 语义相似度阈值
_RETRY_DELAY = 3.0  # API 重试间隔


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def check_plagiarism(paper: dict[str, Any]) -> dict[str, Any]:
    """检查论文重复文本，返回 dim-02 维度结果。

    Args:
        paper: parse_paper.py 输出的结构化 JSON。

    Returns:
        维度结果 JSON（符合统一格式）。
    """
    segments = paper.get("segments", [])
    abstract = _extract_abstract(segments)
    methods = _extract_section(segments, "methods")
    results_text = _extract_section(segments, "results")

    # 提取关键段落用于查询
    queries = []
    if abstract:
        queries.append(("abstract", abstract[:500]))
    if methods:
        queries.append(("methods", methods[:500]))
    if results_text:
        queries.append(("results", results_text[:500]))

    if not queries:
        return _make_result(
            status="passed",
            severity="info",
            findings=[],
            interaction_needed=False,
            detail="未找到可分析的文本段落",
        )

    # 聚合多个 API 结果
    all_matches: list[dict[str, Any]] = []
    for label, query_text in queries:
        matches = _query_all_apis(query_text)
        for m in matches:
            m["source_segment"] = label
        all_matches.extend(matches)

    # 去重（按 DOI 或标题）
    unique = _deduplicate_matches(all_matches)

    # 判定
    findings: list[dict[str, Any]] = []
    max_similarity = 0.0
    for match in unique:
        sim = match.get("similarity", 0.0)
        max_similarity = max(max_similarity, sim)
        if sim >= _SIMILARITY_THRESHOLD:
            findings.append({
                "item": f"疑似重复（{match['source_segment']}）",
                "actual": f"与「{match['title'][:60]}」相似度 {sim:.2f}",
                "suggestion": f"来源: {match['doi'] or match['url'] or '未知'}",
            })

    if max_similarity >= 0.95:
        status, severity = "failed", "critical"
        interaction_needed = True
    elif max_similarity >= _SIMILARITY_THRESHOLD:
        status, severity = "warning", "major"
        interaction_needed = True
    elif max_similarity >= 0.70:
        status, severity = "warning", "minor"
        interaction_needed = False
    else:
        status, severity = "passed", "info"
        interaction_needed = False

    return _make_result(
        status=status,
        severity=severity,
        findings=findings,
        interaction_needed=interaction_needed,
        detail=f"最高相似度: {max_similarity:.2f}, 命中数: {len(findings)}",
    )


# ---------------------------------------------------------------------------
# 文本提取
# ---------------------------------------------------------------------------

def _extract_abstract(segments: list[dict[str, Any]]) -> str:
    for seg in segments:
        if seg.get("type") == "abstract":
            return seg.get("text", "")
    return ""


def _extract_section(segments: list[dict[str, Any]], section_type: str) -> str:
    parts: list[str] = []
    capture = False
    for seg in segments:
        if seg.get("type") == section_type:
            capture = True
        elif capture and seg.get("type") != section_type:
            # 遇到下一个 section 停止
            if seg.get("type") in ("abstract", "introduction", "methods", "results", "discussion", "conclusion", "references"):
                break
        if capture:
            parts.append(seg.get("text", ""))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# API 查询
# ---------------------------------------------------------------------------

def _query_all_apis(query_text: str) -> list[dict[str, Any]]:
    """并行查询 5 个 API，聚合结果。"""
    results: list[dict[str, Any]] = []

    # 每个 API 单独查询（避免并发限制）
    for api_fn in [
        _query_semantic_scholar,
        _query_openalex,
        _query_europepmc,
        _query_arxiv,
        _query_crossref,
    ]:
        try:
            r = api_fn(query_text)
            results.extend(r)
        except Exception:
            pass  # 单个 API 失败不影响整体

    return results


def _query_semantic_scholar(query: str) -> list[dict[str, Any]]:
    """Semantic Scholar API: 100次/5分钟。"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": query[:300], "limit": 5, "fields": "title,doi,url,abstract"}
    with httpx.Client(timeout=_API_TIMEOUT) as client:
        resp = client.get(url, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", [])

    results = []
    for paper in data:
        abstract = paper.get("abstract") or ""
        sim = _compute_similarity(query, abstract)
        results.append({
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "url": paper.get("url", ""),
            "abstract": abstract,
            "similarity": sim,
            "source_api": "semantic_scholar",
        })
    return results


def _query_openalex(query: str) -> list[dict[str, Any]]:
    """OpenAlex API: 无硬限制。"""
    url = "https://api.openalex.org/works"
    params = {"search": query[:300], "per_page": 5}
    with httpx.Client(timeout=_API_TIMEOUT) as client:
        resp = client.get(url, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json().get("results", [])

    results = []
    for work in data:
        title = work.get("title", "")
        abstract_inv = work.get("abstract_inverted_index")
        abstract = _reconstruct_abstract(abstract_inv) if abstract_inv else ""
        doi = work.get("doi", "") or ""
        sim = _compute_similarity(query, abstract or title)
        results.append({
            "title": title,
            "doi": doi.replace("https://doi.org/", ""),
            "url": work.get("id", ""),
            "abstract": abstract,
            "similarity": sim,
            "source_api": "openalex",
        })
    return results


def _query_europepmc(query: str) -> list[dict[str, Any]]:
    """Europe PMC API: 无硬限制。"""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": query[:300], "resultType": "core", "pageSize": 5, "format": "json"}
    with httpx.Client(timeout=_API_TIMEOUT) as client:
        resp = client.get(url, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json().get("resultList", {}).get("result", [])

    results = []
    for item in data:
        abstract = item.get("abstractText", "")
        sim = _compute_similarity(query, abstract)
        results.append({
            "title": item.get("title", ""),
            "doi": item.get("doi", ""),
            "url": item.get("uri", ""),
            "abstract": abstract,
            "similarity": sim,
            "source_api": "europepmc",
        })
    return results


def _query_arxiv(query: str) -> list[dict[str, Any]]:
    """arXiv API: 3秒间隔。"""
    url = "http://export.arxiv.org/api/query"
    params = {"search_query": f"all:{query[:200]}", "max_results": 3}
    with httpx.Client(timeout=_API_TIMEOUT) as client:
        resp = client.get(url, params=params)
        if resp.status_code != 200:
            return []
        text = resp.text

    # 简单 XML 解析
    results = []
    for entry in re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL):
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        arxiv_id = re.search(r"<id>.*?/(.*?)</id>", entry)
        title_text = title.group(1).strip() if title else ""
        abstract = summary.group(1).strip() if summary else ""
        sim = _compute_similarity(query, abstract or title_text)
        results.append({
            "title": title_text,
            "doi": "",
            "url": f"https://arxiv.org/abs/{arxiv_id.group(1).strip()}" if arxiv_id else "",
            "abstract": abstract,
            "similarity": sim,
            "source_api": "arxiv",
        })
    time.sleep(_RETRY_DELAY)  # 遵守 3 秒间隔
    return results


def _query_crossref(query: str) -> list[dict[str, Any]]:
    """CrossRef API: 无硬限制。"""
    url = "https://api.crossref.org/works"
    params = {"query": query[:300], "rows": 5}
    headers = {"User-Agent": "PaperScreening/1.0 (mailto:test@example.com)"}
    with httpx.Client(timeout=_API_TIMEOUT) as client:
        resp = client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            return []
        items = resp.json().get("message", {}).get("items", [])

    results = []
    for item in items:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        abstract = item.get("abstract", "")
        # CrossRef 摘要可能有 HTML 标签
        abstract = re.sub(r"<[^>]+>", "", abstract)
        doi = item.get("DOI", "")
        sim = _compute_similarity(query, abstract or title)
        results.append({
            "title": title,
            "doi": doi,
            "url": item.get("URL", ""),
            "abstract": abstract,
            "similarity": sim,
            "source_api": "crossref",
        })
    return results


# ---------------------------------------------------------------------------
# 相似度计算
# ---------------------------------------------------------------------------

def _compute_similarity(text1: str, text2: str) -> float:
    """计算两段文本的 Jaccard 相似度（基于 n-gram）。"""
    if not text1 or not text2:
        return 0.0

    # 归一化
    t1 = re.sub(r"[^\w\s]", "", text1.lower())
    t2 = re.sub(r"[^\w\s]", "", text2.lower())

    # 生成 trigram 集合
    grams1 = set(_ngrams(t1, 3))
    grams2 = set(_ngrams(t2, 3))

    if not grams1 or not grams2:
        return 0.0

    intersection = grams1 & grams2
    union = grams1 | grams2
    return len(intersection) / len(union) if union else 0.0


def _ngrams(text: str, n: int) -> list[str]:
    """生成字符 n-gram。"""
    tokens = text.split()
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


# ---------------------------------------------------------------------------
# OpenAlex 摘要重建
# ---------------------------------------------------------------------------

def _reconstruct_abstract(inverted_index: dict[str, list[int]]) -> str:
    """从 OpenAlex 倒排索引重建摘要。"""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


# ---------------------------------------------------------------------------
# 去重
# ---------------------------------------------------------------------------

def _deduplicate_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 DOI 或标题去重，保留相似度最高的。"""
    seen: dict[str, dict[str, Any]] = {}
    for m in matches:
        key = m.get("doi") or m.get("title", "")[:50]
        if not key:
            continue
        if key not in seen or m.get("similarity", 0) > seen[key].get("similarity", 0):
            seen[key] = m
    return list(seen.values())


# ---------------------------------------------------------------------------
# 结果构造
# ---------------------------------------------------------------------------

def _make_result(
    status: str,
    severity: str,
    findings: list[dict[str, Any]],
    interaction_needed: bool,
    detail: str,
) -> dict[str, Any]:
    return {
        "dimension_id": "02",
        "dimension_name": "重复文本",
        "status": status,
        "severity": severity,
        "findings": findings,
        "interaction_needed": interaction_needed,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            paper = json.load(f)
    else:
        paper = json.load(sys.stdin)

    result = check_plagiarism(paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
