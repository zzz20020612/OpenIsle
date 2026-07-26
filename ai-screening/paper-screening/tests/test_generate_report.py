"""Tests for generate_report module.

Tests verify the report generator produces correct Markdown output with
proper verdict logic, summary statistics, and per-dimension detail.
"""

from scripts.generate_report import (
    generate_report,
    normalize_dimension,
    parse_dimension_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    dimension_id: str = "01",
    dimension_name: str = "格式与结构",
    status: str = "passed",
    severity: str = "info",
    findings: list | None = None,
    interaction_needed: bool = False,
    user_response: str | None = None,
) -> dict:
    """Build a single dimension result dict with sensible defaults."""
    return {
        "dimension_id": dimension_id,
        "dimension_name": dimension_name,
        "status": status,
        "severity": severity,
        "findings": findings or [],
        "interaction_needed": interaction_needed,
        "user_response": user_response,
    }


def _all_passed(count: int = 9) -> list[dict]:
    """Return *count* results all in 'passed' / 'info' status."""
    names = [
        "格式与结构", "标题与作者", "摘要质量", "引言逻辑",
        "方法完整性", "结果可靠性", "讨论深度", "参考文献", "语言规范",
    ]
    return [
        _make_result(dimension_id=f"{i + 1:02d}", dimension_name=names[i])
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Return type & basic shape
# ---------------------------------------------------------------------------

def test_returns_string():
    """generate_report must return a str."""
    report = generate_report(_all_passed(), "Test Paper", ["Author 1"])
    assert isinstance(report, str)


def test_contains_title():
    """Report must contain the paper title."""
    report = generate_report(_all_passed(), "Deep Learning Survey", ["Zhang Wei"])
    assert "Deep Learning Survey" in report


def test_contains_authors():
    """Report must list all authors."""
    report = generate_report(_all_passed(), "Paper", ["Li Si", "Wang Wu"])
    assert "Li Si" in report
    assert "Wang Wu" in report


def test_contains_timestamp():
    """Report must include a timestamp with YYYY-MM-DD pattern."""
    import re
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert re.search(r"\d{4}-\d{2}-\d{2}", report)


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def test_summary_counts_all_passed():
    """When all pass, summary shows 9 passed, 0 warnings, 0 failed."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "9" in report  # 9/9 passed
    assert "0" in report  # 0 warnings, 0 failed


def test_summary_counts_mixed():
    """Mixed results: correct passed/warning/failed counts in summary."""
    results = [
        _make_result(dimension_id="01", status="passed"),
        _make_result(dimension_id="02", status="passed"),
        _make_result(dimension_id="03", status="warning", severity="minor"),
        _make_result(dimension_id="04", status="failed", severity="major"),
        _make_result(dimension_id="05", status="passed"),
        _make_result(dimension_id="06", status="passed"),
        _make_result(dimension_id="07", status="passed"),
        _make_result(dimension_id="08", status="passed"),
        _make_result(dimension_id="09", status="passed"),
    ]
    report = generate_report(results, "Paper", ["A"])
    # Report should contain count references (2 failed, 1 warning, 6 passed)
    assert "6" in report  # passed count
    assert "1" in report  # warning count


# ---------------------------------------------------------------------------
# Per-dimension detail
# ---------------------------------------------------------------------------

def test_all_dimensions_listed():
    """All 9 dimension names must appear in the report."""
    results = _all_passed()
    report = generate_report(results, "Paper", ["A"])
    for r in results:
        assert r["dimension_name"] in report


def test_dimension_id_shown():
    """Dimension IDs like '01', '02' must appear in section headers."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "01" in report
    assert "09" in report


def test_findings_included():
    """Findings with item/actual/suggestion must appear in report."""
    findings = [
        {"item": "行距", "actual": "1.5倍（要求2倍）", "suggestion": "调整为双倍行距"},
    ]
    result = _make_result(findings=findings)
    report = generate_report([result], "Paper", ["A"])
    assert "行距" in report
    assert "1.5倍" in report
    assert "调整为双倍行距" in report


def test_findings_without_suggestion():
    """Findings with no suggestion should not crash or show 'suggestion'."""
    findings = [{"item": "页边距", "actual": "不符合要求"}]
    result = _make_result(findings=findings)
    report = generate_report([result], "Paper", ["A"])
    assert "页边距" in report


def test_no_findings_shows_clean():
    """Dimension with no findings should show a clean indicator."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "✓" in report or "无" in report


def test_user_response_included():
    """When user_response is provided, it must appear in the report."""
    result = _make_result(
        user_response="已确认基金编号无误",
    )
    report = generate_report([result], "Paper", ["A"])
    assert "已确认基金编号无误" in report


# ---------------------------------------------------------------------------
# Verdict logic — GREEN (✅ 可直接发布)
# ---------------------------------------------------------------------------

def test_verdict_green_all_passed():
    """All passed → green verdict."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "可直接发布" in report


def test_verdict_green_few_warnings():
    """≤3 warnings with no major/critical → green."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="warning", severity="minor")
    results[1] = _make_result(dimension_id="02", status="warning", severity="minor")
    results[2] = _make_result(dimension_id="03", status="warning", severity="minor")
    report = generate_report(results, "Paper", ["A"])
    assert "可直接发布" in report


# ---------------------------------------------------------------------------
# Verdict logic — YELLOW (🟡 建议修改后发布)
# ---------------------------------------------------------------------------

def test_verdict_yellow_many_warnings():
    """>3 warnings (no major/critical) → yellow."""
    results = _all_passed()
    for i in range(4):  # 4 warnings > 3
        results[i] = _make_result(
            dimension_id=f"{i + 1:02d}", status="warning", severity="minor"
        )
    report = generate_report(results, "Paper", ["A"])
    assert "需小修" in report


def test_verdict_yellow_one_major():
    """1 major (no critical) → yellow."""
    results = _all_passed()
    results[0] = _make_result(
        dimension_id="01", status="failed", severity="major"
    )
    report = generate_report(results, "Paper", ["A"])
    assert "需小修" in report


# ---------------------------------------------------------------------------
# Verdict logic — RED (🔴 需管理员审核)
# ---------------------------------------------------------------------------

def test_verdict_red_one_critical():
    """1 critical → red."""
    results = _all_passed()
    results[0] = _make_result(
        dimension_id="01", status="failed", severity="critical"
    )
    report = generate_report(results, "Paper", ["A"])
    assert "需大修" in report


def test_verdict_red_critical_overrides_major():
    """Critical overrides major: still red even with major present."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="failed", severity="critical")
    results[1] = _make_result(dimension_id="02", status="failed", severity="major")
    report = generate_report(results, "Paper", ["A"])
    assert "需大修" in report
    assert "需小修" not in report


# ---------------------------------------------------------------------------
# Reason / recommendation section
# ---------------------------------------------------------------------------

def test_reason_lists_failed_dims():
    """Recommendation section lists failed dimension names."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", dimension_name="格式与结构", status="failed", severity="major")
    report = generate_report(results, "Paper", ["A"])
    assert "格式与结构" in report


def test_reason_lists_warning_dims():
    """Recommendation section lists warning dimension names."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", dimension_name="摘要质量", status="warning", severity="minor")
    report = generate_report(results, "Paper", ["A"])
    assert "摘要质量" in report


def test_reason_all_normal_when_clean():
    """When all pass, reason states everything is normal."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "正常" in report or "各项指标正常" in report


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_results():
    """Empty results list should not crash."""
    report = generate_report([], "Paper", ["A"])
    assert isinstance(report, str)
    assert "Paper" in report


def test_empty_authors():
    """Empty author list should not crash."""
    report = generate_report(_all_passed(), "Paper", [])
    assert isinstance(report, str)
    assert "Paper" in report


def test_single_dimension():
    """Single dimension result should produce valid report."""
    result = [_make_result(dimension_id="01", dimension_name="格式与结构")]
    report = generate_report(result, "Paper", ["A"])
    assert "格式与结构" in report


def test_multiple_findings_per_dimension():
    """Dimension with multiple findings should list all of them."""
    findings = [
        {"item": "字体", "actual": "宋体（要求Arial）"},
        {"item": "字号", "actual": "小四（要求12pt）"},
        {"item": "行距", "actual": "1.5倍（要求2倍）"},
    ]
    result = _make_result(findings=findings)
    report = generate_report([result], "Paper", ["A"])
    assert "字体" in report
    assert "字号" in report
    assert "行距" in report


def test_report_has_markdown_headers():
    """Report must use Markdown heading syntax."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "# " in report  # at least one H1
    assert "## " in report  # at least one H2


def test_report_has_separator():
    """Report should use horizontal rules for visual separation."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "---" in report


# ---------------------------------------------------------------------------
# Risk summary
# ---------------------------------------------------------------------------

def test_risk_summary_all_passed():
    """All-pass report should show clean risk summary."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "风险摘要" in report
    assert "无风险项" in report


def test_risk_summary_with_findings():
    """Report with failed dims should list non-passed dimensions in risk table."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="failed", severity="critical",
                              findings=[{"item": "严重问题", "actual": "发现重大错误"}])
    results[2] = _make_result(dimension_id="03", status="warning", severity="minor",
                              findings=[{"item": "小问题", "actual": "格式偏差"}])
    report = generate_report(results, "Paper", ["A"])
    assert "严重度分布" in report
    assert "非通过维度" in report
    assert "Top 3" in report


def test_risk_summary_top_findings_sorted():
    """Top 3 findings should be sorted by severity (critical before warning)."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="warning", severity="minor",
                              findings=[{"item": "minor问题", "actual": "轻微偏差", "severity": "minor"}])
    results[1] = _make_result(dimension_id="02", status="failed", severity="critical",
                              findings=[{"item": "critical问题", "actual": "严重错误", "severity": "critical"}])
    results[2] = _make_result(dimension_id="03", status="warning", severity="minor",
                              findings=[{"item": "minor问题2", "actual": "另一偏差", "severity": "minor"}])
    report = generate_report(results, "Paper", ["A"])
    top3_start = report.find("Top 3")
    top3_section = report[top3_start:]
    crit_pos = top3_section.find("critical问题")
    minor_pos = top3_section.find("minor问题")
    assert crit_pos < minor_pos


# ---------------------------------------------------------------------------
# Priority recommendations
# ---------------------------------------------------------------------------

def test_priority_recommendations_all_passed():
    """All-pass report should have no priority section."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "修复优先级" not in report


def test_priority_recommendations_ranked():
    """Report with mixed severity findings should show priority-ranked table."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="failed", severity="critical",
                              findings=[{"item": "P0问题", "actual": "严重", "severity": "critical"}])
    results[1] = _make_result(dimension_id="02", status="warning", severity="minor",
                              findings=[{"item": "P2问题", "actual": "轻微", "severity": "minor"}])
    report = generate_report(results, "Paper", ["A"])
    assert "修复优先级" in report
    assert "P0 (紧急)" in report
    assert "P2 (建议)" in report


# ---------------------------------------------------------------------------
# Verdict section (5-level archetypes)
# ---------------------------------------------------------------------------

def test_verdict_publish_archetype():
    """All-pass → Publish archetype."""
    report = generate_report(_all_passed(), "Paper", ["A"])
    assert "决策原型" in report
    assert "Publish" in report


def test_verdict_conditional_archetype():
    """dim-02 failed + dim-04 critical → Conditional archetype."""
    results = _all_passed()
    results[1] = _make_result(dimension_id="02", status="failed", severity="critical")
    results[3] = _make_result(dimension_id="04", status="failed", severity="critical")
    report = generate_report(results, "Paper", ["A"])
    assert "存疑" in report
    assert "Conditional" in report


def test_verdict_reject_archetype():
    """critical ≥ 2 → Reject archetype."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="failed", severity="critical")
    results[1] = _make_result(dimension_id="02", status="failed", severity="critical")
    report = generate_report(results, "Paper", ["A"])
    assert "退稿" in report
    assert "Reject" in report


def test_verdict_triggered_dimensions_listed():
    """Verdict section should list triggered dimensions."""
    results = _all_passed()
    results[0] = _make_result(dimension_id="01", status="failed", severity="major",
                              findings=[{"item": "格式问题", "actual": "行距不对"}])
    report = generate_report(results, "Paper", ["A"])
    assert "触发维度" in report
    assert "格式与结构" in report


# ---------------------------------------------------------------------------
# parse_dimension_json
# ---------------------------------------------------------------------------

class TestParseDimensionJson:
    def test_valid_json(self):
        raw = '{"dimension_id": "01", "dimension_name": "格式", "status": "passed", "severity": "info"}'
        result = parse_dimension_json(raw)
        assert result is not None
        assert result["dimension_id"] == "01"
        assert result["status"] == "passed"

    def test_json_in_code_block(self):
        raw = '```json\n{"dimension_id": "03", "dimension_name": "图像", "status": "warning", "severity": "minor"}\n```'
        result = parse_dimension_json(raw)
        assert result is not None
        assert result["dimension_id"] == "03"
        assert result["status"] == "warning"

    def test_garbage_returns_none(self):
        result = parse_dimension_json("this is not json at all")
        assert result is None

    def test_regex_fallback(self):
        raw = 'Here is the result: dimension_id = "05", status = "failed", severity = "critical". Done.'
        result = parse_dimension_json(raw)
        assert result is not None
        assert result["dimension_id"] == "05"
        assert result["status"] == "failed"

    def test_empty_string(self):
        result = parse_dimension_json("")
        assert result is None


# ---------------------------------------------------------------------------
# normalize_dimension
# ---------------------------------------------------------------------------

class TestNormalizeDimension:
    def test_valid_input_passthrough(self):
        d = {"dimension_id": "01", "dimension_name": "格式", "status": "passed",
             "severity": "info", "findings": [], "interaction_needed": False, "user_response": None}
        result = normalize_dimension(d)
        assert result["status"] == "passed"
        assert result["severity"] == "info"

    def test_invalid_status_corrected(self):
        d = {"dimension_id": "01", "status": "bogus", "severity": "info"}
        result = normalize_dimension(d)
        assert result["status"] == "skipped"

    def test_invalid_severity_corrected(self):
        d = {"dimension_id": "01", "status": "passed", "severity": "unknown"}
        result = normalize_dimension(d)
        assert result["severity"] == "info"

    def test_missing_fields_filled(self):
        d = {}
        result = normalize_dimension(d)
        assert result["dimension_id"] == "00"
        assert result["dimension_name"] == "未知维度"
        assert result["status"] == "skipped"
        assert result["findings"] == []
        assert result["interaction_needed"] is False
        assert result["user_response"] is None

    def test_findings_none_becomes_empty(self):
        d = {"dimension_id": "01", "status": "passed", "severity": "info", "findings": None}
        result = normalize_dimension(d)
        assert result["findings"] == []
