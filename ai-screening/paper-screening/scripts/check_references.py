"""参考文献检测 — DOI 校验 + 引用格式检查 + 自引率统计。

用法: echo '<parsed-json>' | python check_references.py
输出: dim-08 维度结果 JSON
"""

from __future__ import annotations

import json
import re
import sys
import time
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

_API_TIMEOUT = 10.0
_SELF_CITATION_WARNING = 0.10  # 10%
_SELF_CITATION_CRITICAL = 0.20  # 20%


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def check_references(paper: dict[str, Any]) -> dict[str, Any]:
    """检查参考文献质量，返回 dim-08 维度结果。

    Args:
        paper: parse_paper.py 输出的结构化 JSON。

    Returns:
        维度结果 JSON。
    """
    segments = paper.get("segments", [])
    metadata = paper.get("metadata", {})
    authors = metadata.get("authors", [])

    # 提取参考文献段落
    refs_text = _extract_references_section(segments)
    references = _parse_references(refs_text)

    findings: list[dict[str, Any]] = []

    # 1. DOI 格式校验
    doi_issues = _check_doi_format(references)
    findings.extend(doi_issues)

    # 2. 自引率统计
    if authors:
        self_cite_rate = _compute_self_citation_rate(references, authors)
        if self_cite_rate > _SELF_CITATION_CRITICAL:
            findings.append({
                "item": "自引率",
                "actual": f"自引率 {self_cite_rate:.0%}，超过 {_SELF_CITATION_CRITICAL:.0%} 阈值",
                "suggestion": "建议检查是否存在过度自引",
            })
        elif self_cite_rate > _SELF_CITATION_WARNING:
            findings.append({
                "item": "自引率",
                "actual": f"自引率 {self_cite_rate:.0%}，接近阈值",
                "suggestion": "自引率偏高，建议关注",
            })

    # 3. 引用数量检查
    ref_count = len(references)
    if ref_count == 0:
        findings.append({
            "item": "参考文献数量",
            "actual": "未找到参考文献",
            "suggestion": "建议补充参考文献",
        })
    elif ref_count < 10:
        findings.append({
            "item": "参考文献数量",
            "actual": f"仅 {ref_count} 条参考文献",
            "suggestion": "参考文献数量偏少，建议补充",
        })

    # 4. 引用格式一致性检查
    format_issues = _check_reference_format_consistency(references)
    findings.extend(format_issues)

    # 判定
    critical_count = sum(1 for f in findings if "超过" in f.get("actual", ""))
    major_count = len(findings) - critical_count

    if critical_count > 0:
        status, severity = "warning", "major"
    elif major_count >= 1:
        status, severity = "warning", "minor"
    else:
        status, severity = "passed", "info"

    return {
        "dimension_id": "08",
        "dimension_name": "语言引用",
        "status": status,
        "severity": severity,
        "findings": findings,
        "interaction_needed": False,
        "detail": f"参考文献数: {ref_count}, 自引率: {_compute_self_citation_rate(references, authors):.0%}" if authors else f"参考文献数: {ref_count}",
    }


# ---------------------------------------------------------------------------
# 参考文献提取
# ---------------------------------------------------------------------------

def _extract_references_section(segments: list[dict[str, Any]]) -> str:
    """提取参考文献段落。"""
    refs: list[str] = []
    in_refs = False
    for seg in segments:
        if seg.get("type") == "references":
            in_refs = True
        if in_refs:
            refs.append(seg.get("text", ""))
    return "\n".join(refs)


def _parse_references(text: str) -> list[dict[str, Any]]:
    """解析参考文献列表。"""
    if not text:
        return []

    # 尝试按编号分割 [1], [2], ... 或 1., 2., ...
    entries = re.split(r"\n\s*\[\d+\]|\n\s*\d+\.\s", text)

    refs: list[dict[str, Any]] = []
    for entry in entries:
        entry = entry.strip()
        if not entry or len(entry) < 10:
            continue

        # 提取 DOI
        doi_match = re.search(r"(?:doi[:\s]*|DOI[:\s]*)(10\.\d{4,}/\S+)", entry, re.IGNORECASE)
        if not doi_match:
            doi_match = re.search(r"10\.\d{4,}/\S+", entry)

        # 提取标题（启发式：DOI 前的文字）
        title = entry[:100].split(".")[0].strip() if "." in entry else entry[:100]

        refs.append({
            "raw": entry,
            "doi": doi_match.group(1).rstrip(".,;)") if doi_match else None,
            "title": title,
        })

    return refs


# ---------------------------------------------------------------------------
# DOI 校验
# ---------------------------------------------------------------------------

def _check_doi_format(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """检查 DOI 格式有效性。"""
    findings: list[dict[str, Any]] = []
    doi_pattern = re.compile(r"^10\.\d{4,}/\S+$")

    for i, ref in enumerate(references):
        doi = ref.get("doi")
        if doi and not doi_pattern.match(doi):
            findings.append({
                "item": f"DOI 格式 (#{i + 1})",
                "actual": f"DOI 格式无效: {doi}",
                "suggestion": "请检查 DOI 是否正确",
            })

    return findings


# ---------------------------------------------------------------------------
# 自引率计算
# ---------------------------------------------------------------------------

def _compute_self_citation_rate(
    references: list[dict[str, Any]],
    authors: list[str],
) -> float:
    """计算自引率。"""
    if not references or not authors:
        return 0.0

    # 归一化作者姓名
    author_set = set()
    for a in authors:
        # 取姓氏（最后一个词）
        parts = a.strip().split()
        if parts:
            author_set.add(parts[-1].lower())
            author_set.add(a.lower())

    self_cite = 0
    for ref in references:
        raw = ref.get("raw", "").lower()
        for author in author_set:
            if author in raw:
                self_cite += 1
                break

    return self_cite / len(references) if references else 0.0


# ---------------------------------------------------------------------------
# 引用格式一致性
# ---------------------------------------------------------------------------

def _check_reference_format_consistency(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """检查引用格式一致性。"""
    findings: list[dict[str, Any]] = []

    if len(references) < 3:
        return findings

    # 统计有 DOI 和无 DOI 的数量
    with_doi = sum(1 for r in references if r.get("doi"))
    without_doi = len(references) - with_doi

    if with_doi > 0 and without_doi > 0:
        ratio = without_doi / len(references)
        if ratio > 0.5:
            findings.append({
                "item": "引用格式一致性",
                "actual": f"{without_doi}/{len(references)} 条引用缺少 DOI",
                "suggestion": "建议统一引用格式，补充 DOI",
            })

    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            paper = json.load(f)
    else:
        paper = json.load(sys.stdin)

    result = check_references(paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
