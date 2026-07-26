"""科学逻辑检测 — 数值提取 + 摘要-结果一致性比对。

用法: echo '<parsed-json>' | python check_logic.py
输出: dim-04 维度结果 JSON
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def check_logic(paper: dict[str, Any]) -> dict[str, Any]:
    """检查科学逻辑一致性，返回 dim-04 维度结果。

    Args:
        paper: parse_paper.py 输出的结构化 JSON。

    Returns:
        维度结果 JSON。
    """
    segments = paper.get("segments", [])

    abstract_text = _extract_section(segments, "abstract")
    results_text = _extract_section(segments, "results")
    conclusion_text = _extract_section(segments, "conclusion")

    findings: list[dict[str, Any]] = []

    # 1. 摘要-结果数值一致性
    abstract_numbers = _extract_numbers(abstract_text)
    results_numbers = _extract_numbers(results_text)

    mismatches = _compare_numbers(abstract_numbers, results_numbers)
    for m in mismatches:
        findings.append({
            "item": "摘要-结果数值一致性",
            "actual": m["actual"],
            "suggestion": m["suggestion"],
        })

    # 2. P 值检查
    p_issues = _check_p_values(abstract_text, results_text)
    findings.extend(p_issues)

    # 3. 结论过度扩展检查
    overclaim_issues = _check_overclaim(conclusion_text, results_text)
    findings.extend(overclaim_issues)

    # 4. 样本量一致性
    sample_issues = _check_sample_size(abstract_text, results_text)
    findings.extend(sample_issues)

    # 判定
    critical_count = sum(1 for f in findings if "不一致" in f.get("actual", ""))
    major_count = len(findings) - critical_count

    if critical_count >= 2:
        status, severity = "failed", "critical"
        interaction_needed = True
    elif critical_count == 1:
        status, severity = "warning", "major"
        interaction_needed = True
    elif major_count > 0:
        status, severity = "warning", "minor"
        interaction_needed = False
    else:
        status, severity = "passed", "info"
        interaction_needed = False

    return {
        "dimension_id": "04",
        "dimension_name": "科学逻辑",
        "status": status,
        "severity": severity,
        "findings": findings,
        "interaction_needed": interaction_needed,
        "detail": f"数值不一致: {critical_count}, 其他问题: {major_count}",
    }


# ---------------------------------------------------------------------------
# 文本提取
# ---------------------------------------------------------------------------

def _extract_section(segments: list[dict[str, Any]], section_type: str) -> str:
    parts: list[str] = []
    capture = False
    for seg in segments:
        if seg.get("type") == section_type:
            capture = True
        elif capture and seg.get("type") != section_type:
            if seg.get("type") in ("abstract", "introduction", "methods", "results", "discussion", "conclusion", "references"):
                break
        if capture:
            parts.append(seg.get("text", ""))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 数值提取
# ---------------------------------------------------------------------------

def _extract_numbers(text: str) -> list[dict[str, Any]]:
    """从文本中提取数值声明。"""
    if not text:
        return []

    numbers: list[dict[str, Any]] = []

    # P 值
    for match in re.finditer(r"[Pp]\s*[<>=]\s*(\d+\.?\d*)", text):
        numbers.append({
            "type": "p_value",
            "value": float(match.group(1)),
            "raw": match.group(0),
            "context": text[max(0, match.start() - 30):match.end() + 30],
        })

    # 百分比
    for match in re.finditer(r"(\d+\.?\d*)\s*%", text):
        val = float(match.group(1))
        if 0 < val <= 100:
            numbers.append({
                "type": "percentage",
                "value": val,
                "raw": match.group(0),
                "context": text[max(0, match.start() - 30):match.end() + 30],
            })

    # 样本量
    for match in re.finditer(r"(?:n|N|样本)\s*[=:]\s*(\d+)", text):
        numbers.append({
            "type": "sample_size",
            "value": int(match.group(1)),
            "raw": match.group(0),
            "context": text[max(0, match.start() - 30):match.end() + 30],
        })

    # 倍数变化
    for match in re.finditer(r"(\d+\.?\d*)\s*(?:fold|倍)", text, re.IGNORECASE):
        numbers.append({
            "type": "fold_change",
            "value": float(match.group(1)),
            "raw": match.group(0),
            "context": text[max(0, match.start() - 30):match.end() + 30],
        })

    return numbers


# ---------------------------------------------------------------------------
# 数值比对
# ---------------------------------------------------------------------------

def _compare_numbers(
    abstract_nums: list[dict[str, Any]],
    results_nums: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """比对摘要和结果中的数值声明。"""
    mismatches: list[dict[str, Any]] = []

    # 按类型分组
    for num_type in ("percentage", "sample_size", "fold_change"):
        abs_vals = [n for n in abstract_nums if n["type"] == num_type]
        res_vals = [n for n in results_nums if n["type"] == num_type]

        # 简单比对：检查摘要中声明的最大/最小值是否在结果中有对应
        for a_num in abs_vals:
            found_match = False
            for r_num in res_vals:
                # 允许 ±10% 误差（四舍五入）
                tolerance = max(abs(a_num["value"]) * 0.1, 0.01)
                if abs(a_num["value"] - r_num["value"]) <= tolerance:
                    found_match = True
                    break

            if not found_match and res_vals:
                mismatches.append({
                    "actual": f"摘要 {a_num.get('raw', str(a_num['value']))} 在结果段未找到对应数值",
                    "suggestion": "请核实摘要与结果的数据一致性",
                })

    return mismatches


# ---------------------------------------------------------------------------
# P 值检查
# ---------------------------------------------------------------------------

def _check_p_values(abstract: str, results: str) -> list[dict[str, Any]]:
    """检查 P 值报告的一致性。"""
    findings: list[dict[str, Any]] = []

    # 摘要中的 P 值声明
    abs_p = re.findall(r"[Pp]\s*[<>=]\s*(\d+\.?\d*)", abstract)
    res_p = re.findall(r"[Pp]\s*[<>=]\s*(\d+\.?\d*)", results)

    if abs_p and not res_p:
        findings.append({
            "item": "P 值报告",
            "actual": f"摘要声明 P 值 ({', '.join(abs_p)})，但结果段未报告",
            "suggestion": "建议在结果段补充具体 P 值",
        })

    # 检查摘要中的 P < 0.05 是否与结果一致
    for p_str in abs_p:
        p_val = float(p_str)
        if p_val <= 0.05:
            # 摘要声称显著，检查结果段是否有矛盾
            for r_str in res_p:
                r_val = float(r_str)
                if r_val >= 0.05:
                    findings.append({
                        "item": "P 值不一致",
                        "actual": f"摘要 P={p_val}（显著），结果 P={r_val}（不显著）",
                        "suggestion": "摘要与结果的 P 值矛盾，请核实",
                    })

    return findings


# ---------------------------------------------------------------------------
# 过度声明检查
# ---------------------------------------------------------------------------

_OVERCLAIM_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:prove|proves|proven)\b|证明", "「prove」是强结论词，需确认是否有充分证据支撑"),
    (r"\b(?:definitively)\b|明确地", "「definitively」是强结论词，需确认证据充分性"),
    (r"\b(?:for the first time)\b|首次", "「首次」声明需确认是否确为首创"),
    (r"\b(?:no alternative)\b|没有替代", "「没有替代」是绝对声明，需确认是否排除所有可能性"),
    (r"\b(?:unprecedented)\b|史无前例", "「unprecedented」是极端声明，需确认是否有足够比较基准"),
    (r"\b(?:revolutionary|paradigm.shift)\b|革命性|范式转移", "「revolutionary/paradigm shift」需确认是否有充分理论支撑"),
    (r"\b(?:100%|完全|entirely|completely)\b", "「100%/完全」是绝对表述，需确认是否排除所有例外"),
    (r"\b(?:always|never)\b|总是|从不", "「always/never」是极端表述，需确认是否有足够实验证据"),
]


def _check_overclaim(conclusion: str, results: str) -> list[dict[str, Any]]:
    """检查结论是否过度扩展。"""
    findings: list[dict[str, Any]] = []

    combined = conclusion + " " + results

    for pattern, suggestion in _OVERCLAIM_PATTERNS:
        matches = re.findall(pattern, combined, re.IGNORECASE)
        if matches:
            findings.append({
                "item": "结论过度扩展",
                "actual": f"发现「{matches[0]}」等强结论表述",
                "suggestion": suggestion,
            })

    return findings


# ---------------------------------------------------------------------------
# 样本量检查
# ---------------------------------------------------------------------------

def _check_sample_size(abstract: str, results: str) -> list[dict[str, Any]]:
    """检查样本量一致性。"""
    findings: list[dict[str, Any]] = []

    abs_samples = re.findall(r"(?:n|N|样本)\s*[=:]\s*(\d+)", abstract)
    res_samples = re.findall(r"(?:n|N|样本)\s*[=:]\s*(\d+)", results)

    if abs_samples and res_samples:
        abs_val = int(abs_samples[0])
        res_val = int(res_samples[0])
        if abs_val != res_val:
            findings.append({
                "item": "样本量不一致",
                "actual": f"摘要样本量 {abs_val}，结果样本量 {res_val}",
                "suggestion": "请核实摘要与结果的样本量是否一致",
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

    result = check_logic(paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
