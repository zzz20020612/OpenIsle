"""报告生成器 — 将 9 维度分析结果转为 Markdown 审核报告。

Verdict logic (traffic-light triage):
  ✅ 可直接发布 (Publish)       — no critical, no major, warning ≤ 3
  🟡 需小修 (Minor Revision)    — no critical, has major or warning > 3
  🔴 需大修 (Major Revision)    — has critical (non-integrity), or failed ≥ 3
  ❌ 存疑 (Conditional)         — dim-02 failed + dim-04 critical (integrity)
  🚫 退稿 (Reject)              — critical ≥ 2 or failed ≥ 5

Enhanced features (v2 — inspired by PaperDecision analysis):
  - Confidence scoring: 0-100 score based on severity distribution
  - Anti-intuitive findings: detects high-severity-but-few-issues or low-severity-but-many-issues
  - Data quality summary: completeness metrics for parsed paper data
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_VALID_STATUSES = frozenset({"passed", "warning", "failed", "skipped"})
_VALID_SEVERITIES = frozenset({"info", "minor", "major", "critical"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SEVERITY_ORDER: dict[str, int] = {"critical": 0, "major": 1, "warning": 2}


# ---------------------------------------------------------------------------
# Confidence scoring (inspired by PaperDecision's weight multiplier system)
# ---------------------------------------------------------------------------

def _compute_confidence(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute a 0-100 confidence score for the screening verdict.

    Scoring logic:
    - Start at 100
    - Each critical finding: -25
    - Each major finding: -15
    - Each warning finding: -5
    - Bonus: +5 if all 9 dimensions returned results (no skipped)
    - Penalty: -10 per skipped dimension

    Returns:
        Dict with score (int), level (str), and breakdown (list[str]).
    """
    score = 100
    breakdown: list[str] = []

    skipped_count = sum(1 for r in results if r.get("status") == "skipped")
    if skipped_count == 0:
        score += 5
        breakdown.append("全部 9 维度完成: +5")
    else:
        penalty = skipped_count * 10
        score -= penalty
        breakdown.append(f"跳过 {skipped_count} 个维度: -{penalty}")

    for r in results:
        dim_severity = r.get("severity", "info")
        findings = r.get("findings", [])
        for f in findings:
            # findings 可能没有独立的 severity 字段，回退到维度级别的 severity
            sev = f.get("severity") or dim_severity
            if sev == "critical":
                score -= 25
                breakdown.append(f"Critical ({r['dimension_name']}): -25")
            elif sev == "major":
                score -= 15
                breakdown.append(f"Major ({r['dimension_name']}): -15")
            elif sev == "warning":
                score -= 5
                breakdown.append(f"Warning ({r['dimension_name']}): -5")

    score = max(0, min(100, score))

    if score >= 80:
        level = "高置信度"
    elif score >= 60:
        level = "中置信度"
    elif score >= 40:
        level = "低置信度"
    else:
        level = "极低置信度"

    return {"score": score, "level": level, "breakdown": breakdown}


def generate_report(
    results: list[dict[str, Any]],
    title: str,
    authors: list[str],
) -> str:
    """生成 Markdown 格式的论文初审报告。

    Args:
        results: 每个维度的分析结果列表，每条包含 dimension_id, dimension_name,
                 status, severity, findings, interaction_needed, user_response.
        title:   论文标题。
        authors: 作者列表。

    Returns:
        完整的 Markdown 报告字符串。
    """
    passed = sum(1 for r in results if r["status"] == "passed")
    warnings = sum(1 for r in results if r["status"] == "warning")
    failed = sum(1 for r in results if r["status"] == "failed")

    verdict_info = _determine_verdict(results)
    verdict_str = verdict_info["verdict"]
    confidence = _compute_confidence(results)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = [
        "# 论文初审完善报告\n",
        "## 概览\n",
        f"- **论文标题**: {title}",
        f"- **作者**: {', '.join(authors)}" if authors else "- **作者**: 未提供",
        f"- **审核时间**: {timestamp}",
        f"- **通过项**: {passed}/{len(results)}",
        f"- **提醒项**: {warnings}/{len(results)}",
        f"- **风险项**: {failed}/{len(results)}",
        f"- **综合判定**: {verdict_str}",
        f"- **置信度**: {confidence['score']}/100 ({confidence['level']})\n",
        "---\n",
    ]

    # Risk summary section
    lines.extend(_risk_summary(results))

    # Anti-intuitive findings section
    lines.extend(_anti_intuitive_findings(results))

    # Detail section
    lines.append("## 明细（按维度）\n")

    for result in results:
        status_icon = _status_icon(result["status"])
        lines.append(
            f"### [{status_icon}] 维度{result['dimension_id']}: {result['dimension_name']}"
        )
        lines.append(f"**状态**: {result['status']}\n")

        if result["findings"]:
            for finding in result["findings"]:
                item = finding.get("item", "")
                actual = finding.get("actual", "")
                lines.append(f"- {item}: {actual}")
                if finding.get("suggestion"):
                    lines.append(f"  - 建议: {finding['suggestion']}")
        else:
            lines.append("- 无发现问题 ✓")

        if result.get("user_response"):
            lines.append(f"\n**用户回应**: {result['user_response']}")

        lines.append("")

    # Priority recommendations section
    lines.extend(_priority_recommendations(results))

    # Enhanced verdict section
    lines.extend(_format_verdict_section(verdict_info, results))

    # Confidence breakdown section
    lines.extend(_format_confidence_section(confidence))

    lines.extend([
        "---\n",
        "*报告由论文初筛 AI Skill 自动生成*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Verdict engine
# ---------------------------------------------------------------------------

def _determine_verdict(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Determine verdict with archetype, reason, and triggering dimensions.

    Returns:
        Dict with keys: verdict (str), archetype (str), reason (str),
        triggered (list[str]).
    """
    critical_dims = [r for r in results if r["severity"] == "critical"]
    major_dims = [r for r in results if r["severity"] == "major"]
    warning_dims = [r for r in results if r["status"] == "warning"]
    failed_dims = [r for r in results if r["status"] == "failed"]

    critical_count = len(critical_dims)
    major_count = len(major_dims)
    warning_count = len(warning_dims)
    failed_count = len(failed_dims)

    dim02_failed = any(r["dimension_id"] == "02" and r["status"] == "failed" for r in results)
    dim04_critical = any(r["dimension_id"] == "04" and r["severity"] == "critical" for r in results)
    # Non-integrity critical: any critical that is NOT dim-04
    critical_non_integrity = [
        r for r in critical_dims if r["dimension_id"] != "04"
    ]

    triggered_ids: list[str] = []

    # ❌ 存疑 — dim-02 failed + dim-04 critical
    if dim02_failed and dim04_critical:
        triggered_ids.extend(_collect_triggered(results, {"02", "04"}))
        return {
            "verdict": "❌ 存疑",
            "archetype": "Conditional",
            "reason": (
                f"维度02（重复率）未通过且维度04（逻辑严谨性）存在严重问题，"
                f"存在学术诚信风险，建议由管理员人工复核"
            ),
            "triggered": triggered_ids,
        }

    # 🚫 退稿 — critical ≥ 2 or failed ≥ 5
    if critical_count >= 2 or failed_count >= 5:
        triggered_ids.extend(_collect_triggered(results, None))
        return {
            "verdict": "🚫 退稿",
            "archetype": "Reject",
            "reason": (
                f"存在 {critical_count} 项严重问题、{failed_count} 项未通过维度，"
                f"论文质量不达标，建议退稿"
            ),
            "triggered": triggered_ids,
        }

    # 🔴 需大修 — has critical (non-integrity) or failed ≥ 3
    if critical_non_integrity or failed_count >= 3:
        triggered_ids.extend(_collect_triggered(results, None))
        crit_names = [r["dimension_name"] for r in critical_non_integrity]
        fail_names = [r["dimension_name"] for r in failed_dims]
        parts: list[str] = []
        if crit_names:
            parts.append(f"严重问题维度: {', '.join(crit_names)}")
        if fail_names:
            parts.append(f"未通过维度: {', '.join(fail_names)}")
        return {
            "verdict": "🔴 需大修",
            "archetype": "Major Revision",
            "reason": "；".join(parts),
            "triggered": triggered_ids,
        }

    # 🟡 需小修 — has major or warning > 3
    if major_count > 0 or warning_count > 3:
        triggered_ids.extend(_collect_triggered(results, None))
        parts = []
        if major_count > 0:
            maj_names = [r["dimension_name"] for r in major_dims]
            parts.append(f"重要问题维度: {', '.join(maj_names)}")
        if warning_count > 3:
            parts.append(f"提醒项过多 ({warning_count})")
        return {
            "verdict": "🟡 需小修",
            "archetype": "Minor Revision",
            "reason": "；".join(parts),
            "triggered": triggered_ids,
        }

    # ✅ 可直接发布
    return {
        "verdict": "✅ 可直接发布",
        "archetype": "Publish",
        "reason": "各项指标正常，论文可直接发布",
        "triggered": [],
    }


def _collect_triggered(
    results: list[dict[str, Any]],
    dim_ids: set[str] | None,
) -> list[str]:
    """Collect dimension IDs that contributed to a non-passing verdict.

    Args:
        results: All dimension results.
        dim_ids: If provided, only include these specific IDs. If None,
                 include all non-passed dimensions.
    """
    triggered: list[str] = []
    for r in results:
        if r["status"] == "passed":
            continue
        if dim_ids is not None and r["dimension_id"] not in dim_ids:
            continue
        triggered.append(r["dimension_id"])
    return triggered


# ---------------------------------------------------------------------------
# Risk summary
# ---------------------------------------------------------------------------

def _risk_summary(results: list[dict[str, Any]]) -> list[str]:
    """Build the risk summary section showing non-passed dimensions and severity.

    Args:
        results: All dimension results.

    Returns:
        Lines for the risk summary section, or empty list if all passed.
    """
    non_passed = [r for r in results if r["status"] != "passed"]
    if not non_passed:
        return [
            "## 风险摘要\n",
            "各维度均通过，无风险项。\n",
        ]

    # Severity distribution
    critical = sum(1 for r in results if r["severity"] == "critical")
    major = sum(1 for r in results if r["severity"] == "major")
    warning = sum(1 for r in results if r["status"] == "warning")

    lines: list[str] = [
        "## 风险摘要\n",
        f"**严重度分布**: critical: {critical} | major: {major} | warning: {warning}\n",
        "### 非通过维度\n",
        "| 维度 | 状态 | 严重度 | 发现数 |",
        "|------|------|--------|--------|",
    ]

    for r in non_passed:
        finding_count = len(r.get("findings", []))
        lines.append(
            f"| 维度{r['dimension_id']} {r['dimension_name']} "
            f"| {r['status']} | {r['severity']} | {finding_count} |"
        )

    # Top 3 most severe findings
    top_findings = _top_findings(results, n=3)
    if top_findings:
        lines.append("\n### 最严重发现（Top 3）\n")
        for i, (dim_name, finding) in enumerate(top_findings, 1):
            item = finding.get("item", "未知")
            actual = finding.get("actual", "")
            sev = finding.get("severity", "warning")
            lines.append(f"{i}. **[{sev}]** {dim_name} — {item}: {actual}")

    lines.append("")
    return lines


def _top_findings(
    results: list[dict[str, Any]],
    n: int = 3,
) -> list[tuple[str, dict[str, str]]]:
    """Return the N most severe findings across all dimensions.

    Args:
        results: All dimension results.
        n: Number of top findings to return.

    Returns:
        List of (dimension_name, finding_dict) tuples sorted by severity.
    """
    all_findings: list[tuple[str, int, dict[str, str]]] = []
    for r in results:
        for finding in r.get("findings", []):
            sev = finding.get("severity", "warning")
            order = _SEVERITY_ORDER.get(sev, 99)
            all_findings.append((r["dimension_name"], order, finding))

    all_findings.sort(key=lambda x: x[1])
    return [(fn, f) for fn, _, f in all_findings[:n]]


# ---------------------------------------------------------------------------
# Priority recommendations
# ---------------------------------------------------------------------------

_SEVERITY_TO_PRIORITY: dict[str, str] = {
    "critical": "P0 (紧急)",
    "major": "P1 (重要)",
    "warning": "P2 (建议)",
}


def _priority_recommendations(results: list[dict[str, Any]]) -> list[str]:
    """Build priority-ranked recommendations from all findings.

    Args:
        results: All dimension results.

    Returns:
        Lines for the priority section, or empty list if no findings.
    """
    ranked: list[tuple[str, str, str, str]] = []
    for r in results:
        for finding in r.get("findings", []):
            sev = finding.get("severity", "warning")
            priority = _SEVERITY_TO_PRIORITY.get(sev, "P2 (建议)")
            item = finding.get("item", "未知")
            dim_name = r["dimension_name"]
            ranked.append((sev, priority, dim_name, item))

    # Sort by severity order
    ranked.sort(key=lambda x: _SEVERITY_ORDER.get(x[0], 99))

    if not ranked:
        return []

    lines: list[str] = [
        "---\n",
        "## 修复优先级\n",
        "| 优先级 | 维度 | 发现项 |",
        "|--------|------|--------|",
    ]

    for sev, priority, dim_name, item in ranked:
        lines.append(f"| {priority} | {dim_name} | {item} |")

    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Verdict section formatter
# ---------------------------------------------------------------------------

def _format_verdict_section(
    verdict_info: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[str]:
    """Format the enhanced verdict section with structured reasoning.

    Args:
        verdict_info: The dict returned by _determine_verdict().
        results: All dimension results (for triggered dimension details).

    Returns:
        Lines for the verdict section.
    """
    triggered = verdict_info.get("triggered", [])
    triggered_dims = [r for r in results if r["dimension_id"] in triggered]

    lines: list[str] = [
        "---\n",
        "## 分流建议\n",
        f"**判定**: {verdict_info['verdict']}",
        f"**决策原型**: {verdict_info['archetype']}\n",
    ]

    if triggered_dims:
        lines.append("**触发维度**:\n")
        for r in triggered_dims:
            severity = r.get("severity", "unknown")
            finding_summary = _finding_summary(r)
            lines.append(f"- {r['dimension_name']}: {severity} — {finding_summary}")

    lines.append(f"\n**综合理由**: {verdict_info['reason']}\n")
    return lines


def _finding_summary(result: dict[str, Any]) -> str:
    """Generate a short summary string from a dimension's findings.

    Args:
        result: A single dimension result dict.

    Returns:
        Comma-separated finding items, or "无" if no findings.
    """
    findings = result.get("findings", [])
    if not findings:
        return "无"
    items = [f.get("item", "") for f in findings if f.get("item")]
    return ", ".join(items) if items else "无"


# ---------------------------------------------------------------------------
# Confidence breakdown section
# ---------------------------------------------------------------------------

def _format_confidence_section(confidence: dict[str, Any]) -> list[str]:
    """Format the confidence scoring breakdown section.

    Args:
        confidence: Dict from _compute_confidence() with score, level, breakdown.

    Returns:
        Lines for the confidence section.
    """
    lines: list[str] = [
        "---\n",
        "## 置信度分析\n",
        f"**总分**: {confidence['score']}/100 — {confidence['level']}\n",
    ]

    if confidence["breakdown"]:
        lines.append("| 项目 | 影响 |")
        lines.append("|------|------|")
        for item in confidence["breakdown"]:
            lines.append(f"| {item} |")

    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Anti-intuitive findings (inspired by PaperDecision Section 7)
# ---------------------------------------------------------------------------

def _anti_intuitive_findings(results: list[dict[str, Any]]) -> list[str]:
    """Detect counter-intuitive patterns in screening results.

    Patterns detected:
    1. High severity but few issues: critical/major findings in only 1 dimension
       but overall verdict is "退稿" — may indicate over-aggressive screening
    2. Low severity but many issues: many warnings across many dimensions
       but no critical/major — may indicate systematic quality concerns
    3. Academic integrity signals: dim-02 (plagiarism) + dim-04 (logic) both
       showing problems — strong indicator of research misconduct
    """
    lines: list[str] = []

    critical_dims = [r for r in results if r["severity"] == "critical"]
    major_dims = [r for r in results if r["severity"] == "major"]
    warning_dims = [r for r in results if r["status"] == "warning"]
    failed_dims = [r for r in results if r["status"] == "failed"]

    insights: list[str] = []

    if len(critical_dims) >= 2 and len(failed_dims) <= 2:
        dim_names = [r["dimension_name"] for r in critical_dims]
        insights.append(
            f"⚠️ **多维度严重问题**: {', '.join(dim_names)} 同时存在 critical 级别问题，"
            f"建议优先核查这些维度"
        )

    if len(warning_dims) >= 5 and len(critical_dims) == 0 and len(major_dims) == 0:
        dim_names = [r["dimension_name"] for r in warning_dims]
        insights.append(
            f"⚠️ **系统性质量风险**: {len(warning_dims)} 个维度存在 warning，"
            f"虽无严重问题，但累计效应值得重视"
        )

    dim02_failed = any(r["dimension_id"] == "02" and r["status"] == "failed" for r in results)
    dim04_critical = any(r["dimension_id"] == "04" and r["severity"] == "critical" for r in results)
    if dim02_failed and dim04_critical:
        insights.append(
            "🚨 **学术诚信嫌疑**: 重复文本 + 科学逻辑严重问题同时出现，"
            "强烈建议人工复核"
        )

    dim05_critical = any(r["dimension_id"] == "05" and r["severity"] == "critical" for r in results)
    dim06_critical = any(r["dimension_id"] == "06" and r["severity"] == "critical" for r in results)
    if dim05_critical and dim06_critical:
        insights.append(
            "🚨 **合规风险**: 伦理法规 + 敏感内容双重红线，"
            "必须人工审核后方可继续"
        )

    if not insights:
        return []

    lines = [
        "---\n",
        "## 反直觉发现\n",
    ]
    for insight in insights:
        lines.append(f"- {insight}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Status icon helper
# ---------------------------------------------------------------------------

def _status_icon(status: str) -> str:
    """Map status string to emoji icon."""
    return {"passed": "✅", "warning": "🟡", "failed": "🔴"}.get(status, "⚪")


# ---------------------------------------------------------------------------
# Robust JSON parsing & normalization (for external callers)
# ---------------------------------------------------------------------------

def parse_dimension_json(raw: str) -> dict | None:
    """从 LLM 输出字符串中解析维度结果 JSON，失败时用正则兜底。

    PaperDecision 的 parse_decision_json() 策略：先尝试直接 json.loads，
    失败后用正则提取关键字段。返回 None 表示完全无法解析。

    Args:
        raw: LLM 原始输出字符串，可能包含 Markdown 代码块等噪声。

    Returns:
        解析后的 dict，或 None。
    """
    text = raw.strip()

    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, TypeError):
        pass

    logger.warning("JSON 解析失败，尝试正则兜底提取")

    def _pick(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text)
        return m.group(1).strip().strip("\"'") if m else default

    dimension_id = _pick(r'"?dimension_id"?\s*[:=]\s*"?(\d+)"?')
    dimension_name = _pick(r'"?dimension_name"?\s*[:=]\s*"?([^"\n,}]+)"?')
    status = _pick(r'"?status"?\s*[:=]\s*"(passed|warning|failed|skipped)"')
    severity = _pick(r'"?severity"?\s*[:=]\s*"(info|minor|major|critical)"')

    if not (dimension_id or dimension_name or status):
        return None

    return {
        "dimension_id": dimension_id or "00",
        "dimension_name": dimension_name or "未知维度",
        "status": status or "skipped",
        "severity": severity or "info",
        "findings": [],
        "interaction_needed": False,
        "user_response": None,
    }


def normalize_dimension(result: dict) -> dict:
    """校验并补全维度结果字段，确保 status/severity 合法。

    Args:
        result: 维度分析结果 dict，可能缺少字段或含非法值。

    Returns:
        校验后的 dict，缺失字段填充默认值，非法值修正为安全默认值。
    """
    status = result.get("status", "skipped")
    if status not in _VALID_STATUSES:
        logger.warning("非法 status '%s'，修正为 'skipped'", status)
        status = "skipped"

    severity = result.get("severity", "info")
    if severity not in _VALID_SEVERITIES:
        logger.warning("非法 severity '%s'，修正为 'info'", severity)
        severity = "info"

    return {
        "dimension_id": str(result.get("dimension_id", "00")),
        "dimension_name": str(result.get("dimension_name", "未知维度")),
        "status": status,
        "severity": severity,
        "findings": result.get("findings") or [],
        "interaction_needed": bool(result.get("interaction_needed", False)),
        "user_response": result.get("user_response"),
    }
