"""Tests for check_logic.py — dim-04 科学逻辑检测。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_logic import (
    _check_overclaim,
    _check_p_values,
    _check_sample_size,
    _compare_numbers,
    _extract_numbers,
    _extract_section,
    check_logic,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_paper(abstract: str = "", results: str = "", conclusion: str = "") -> dict:
    segments = []
    if abstract:
        segments.append({"type": "abstract", "text": abstract})
    if results:
        segments.append({"type": "results", "text": results})
    if conclusion:
        segments.append({"type": "conclusion", "text": conclusion})
    return {"metadata": {"title": "Test"}, "segments": segments, "images": [], "tables": []}


# ---------------------------------------------------------------------------
# Number extraction
# ---------------------------------------------------------------------------

class TestExtractNumbers:
    def test_p_value(self):
        nums = _extract_numbers("P < 0.05")
        assert any(n["type"] == "p_value" for n in nums)

    def test_percentage(self):
        nums = _extract_numbers("Accuracy was 95.3%")
        assert any(n["type"] == "percentage" and n["value"] == 95.3 for n in nums)

    def test_sample_size(self):
        nums = _extract_numbers("n = 120 participants")
        assert any(n["type"] == "sample_size" and n["value"] == 120 for n in nums)

    def test_fold_change(self):
        nums = _extract_numbers("3.5 fold increase")
        assert any(n["type"] == "fold_change" for n in nums)

    def test_empty(self):
        assert _extract_numbers("") == []


# ---------------------------------------------------------------------------
# Number comparison
# ---------------------------------------------------------------------------

class TestCompareNumbers:
    def test_matching(self):
        abs_nums = [{"type": "percentage", "value": 95.0}]
        res_nums = [{"type": "percentage", "value": 95.3}]
        # 0.3 difference < 10% of 95.0 = 9.5
        assert _compare_numbers(abs_nums, res_nums) == []

    def test_mismatch(self):
        abs_nums = [{"type": "percentage", "value": 95.0, "raw": "95%"}]
        res_nums = [{"type": "percentage", "value": 70.0, "raw": "70%"}]
        mismatches = _compare_numbers(abs_nums, res_nums)
        assert len(mismatches) == 1


# ---------------------------------------------------------------------------
# P-value checks
# ---------------------------------------------------------------------------

class TestPValues:
    def test_consistent(self):
        issues = _check_p_values("P < 0.001", "P = 0.0005")
        assert len(issues) == 0

    def test_missing_in_results(self):
        issues = _check_p_values("P < 0.05", "")
        assert len(issues) == 1

    def test_contradiction(self):
        issues = _check_p_values("P < 0.05", "P = 0.12")
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Overclaim
# ---------------------------------------------------------------------------

class TestOverclaim:
    def test_no_overclaim(self):
        issues = _check_overclaim("The results suggest improvement", "")
        assert len(issues) == 0

    def test_prove(self):
        issues = _check_overclaim("This proves our hypothesis", "")
        assert len(issues) == 1

    def test_first_time(self):
        issues = _check_overclaim("For the first time, we show", "")
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Sample size
# ---------------------------------------------------------------------------

class TestSampleSize:
    def test_consistent(self):
        issues = _check_sample_size("n = 100", "n = 100")
        assert len(issues) == 0

    def test_inconsistent(self):
        issues = _check_sample_size("n = 100", "n = 80")
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Full check
# ---------------------------------------------------------------------------

class TestCheckLogic:
    def test_clean_paper(self):
        paper = _make_paper(
            abstract="P < 0.05. Accuracy 95%.",
            results="P = 0.03. Accuracy 94.8%.",
        )
        result = check_logic(paper)
        assert result["dimension_id"] == "04"
        assert result["status"] == "passed"

    def test_mismatch(self):
        paper = _make_paper(
            abstract="P < 0.001. Accuracy 95%.",
            results="P = 0.12. Accuracy 70%.",
        )
        result = check_logic(paper)
        assert result["status"] in ("warning", "failed")

    def test_result_format(self):
        paper = _make_paper()
        result = check_logic(paper)
        assert "dimension_id" in result
        assert "status" in result
        assert "findings" in result
