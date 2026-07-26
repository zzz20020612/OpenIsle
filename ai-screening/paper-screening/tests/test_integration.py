"""Integration tests for the full paper-screening pipeline.

Verifies end-to-end flow: parse → generate report.
Uses real sample files (no mocks) to validate the complete workflow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_report import generate_report
from scripts.parse_paper import parse_paper

SAMPLES = Path(__file__).resolve().parent.parent / "test_samples"


def _mock_9d_all_pass() -> list[dict]:
    """Generate mock 9-dimension results where every dimension passes."""
    return [
        {
            "dimension_id": f"{i:02d}",
            "dimension_name": f"维度{i}",
            "status": "passed",
            "severity": "info",
            "findings": [],
            "interaction_needed": False,
            "user_response": None,
        }
        for i in range(1, 10)
    ]


def _mock_9d_with_warnings() -> list[dict]:
    """Generate mock 9-dimension results with some warnings."""
    results = []
    for i in range(1, 10):
        if i == 3:
            results.append(
                {
                    "dimension_id": f"{i:02d}",
                    "dimension_name": f"维度{i}",
                    "status": "warning",
                    "severity": "warning",
                    "findings": [{"item": "测试项", "actual": "发现一个问题"}],
                    "interaction_needed": False,
                    "user_response": None,
                }
            )
        elif i == 7:
            results.append(
                {
                    "dimension_id": f"{i:02d}",
                    "dimension_name": f"维度{i}",
                    "status": "failed",
                    "severity": "critical",
                    "findings": [{"item": "严重问题", "actual": "需要管理员审核"}],
                    "interaction_needed": False,
                    "user_response": None,
                }
            )
        else:
            results.append(
                {
                    "dimension_id": f"{i:02d}",
                    "dimension_name": f"维度{i}",
                    "status": "passed",
                    "severity": "info",
                    "findings": [],
                    "interaction_needed": False,
                    "user_response": None,
                }
            )
    return results


# ---------------------------------------------------------------------------
# Full pipeline: TXT
# ---------------------------------------------------------------------------


class TestPipelineTxt:
    """End-to-end: TXT file → parse → report."""

    def test_full_pipeline_txt(self):
        txt_file = SAMPLES / "sample.txt"
        if not txt_file.exists():
            pytest.skip("测试文件不存在")

        # Step 1: Parse
        parsed = parse_paper(str(txt_file))
        assert "metadata" in parsed
        assert len(parsed["segments"]) > 0

        # Step 2: Generate report with mock 9-dimension results (all pass)
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        assert isinstance(report, str)
        assert len(report) > 100
        assert "可直接发布" in report
        assert parsed["metadata"]["title"] in report

    def test_pipeline_report_contains_dimensions(self):
        txt_file = SAMPLES / "sample.txt"
        if not txt_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(txt_file))
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        # Report should mention all 9 dimensions
        for i in range(1, 10):
            assert f"维度{i:02d}" in report


# ---------------------------------------------------------------------------
# Full pipeline: DOCX
# ---------------------------------------------------------------------------


class TestPipelineDocx:
    """End-to-end: DOCX file → parse → report."""

    def test_full_pipeline_docx(self):
        docx_file = SAMPLES / "sample.docx"
        if not docx_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(docx_file))
        assert "metadata" in parsed
        assert len(parsed["segments"]) > 0

        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        assert isinstance(report, str)
        assert len(report) > 100
        assert "可直接发布" in report

    def test_pipeline_authors_propagated(self):
        docx_file = SAMPLES / "sample.docx"
        if not docx_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(docx_file))
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        # Authors from DOCX should appear in report
        for author in parsed["metadata"]["authors"]:
            assert author in report


# ---------------------------------------------------------------------------
# Full pipeline: PDF
# ---------------------------------------------------------------------------


class TestPipelinePdf:
    """End-to-end: PDF file → parse → report."""

    def test_full_pipeline_pdf(self):
        pdf_file = SAMPLES / "sample.pdf"
        if not pdf_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(pdf_file))
        assert "metadata" in parsed
        assert len(parsed["segments"]) > 0

        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        assert isinstance(report, str)
        assert len(report) > 100
        assert "可直接发布" in report


# ---------------------------------------------------------------------------
# Full pipeline: LaTeX
# ---------------------------------------------------------------------------


class TestPipelineTex:
    """End-to-end: LaTeX file → parse → report."""

    def test_full_pipeline_tex(self):
        tex_file = SAMPLES / "sample.tex"
        if not tex_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(tex_file))
        assert "metadata" in parsed
        assert len(parsed["segments"]) > 0

        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        assert isinstance(report, str)
        assert len(report) > 100
        assert "可直接发布" in report

    def test_pipeline_title_from_latex(self):
        tex_file = SAMPLES / "sample.tex"
        if not tex_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(tex_file))
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )

        assert parsed["metadata"]["title"] in report


# ---------------------------------------------------------------------------
# Verdict logic via report
# ---------------------------------------------------------------------------


class TestVerdictIntegration:
    """Verify report verdict matches severity-driven logic."""

    def test_all_pass_gives_green(self):
        txt_file = SAMPLES / "sample.txt"
        if not txt_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(txt_file))
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )
        assert "✅ 可直接发布" in report

    def test_critical_gives_red(self):
        txt_file = SAMPLES / "sample.txt"
        if not txt_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(txt_file))
        report = generate_report(
            _mock_9d_with_warnings(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )
        assert "🔴 需大修" in report
        assert "可直接发布" not in report

    def test_no_authors_uses_fallback(self):
        txt_file = SAMPLES / "sample.txt"
        if not txt_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(txt_file))
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            [],  # empty authors
        )
        assert "未提供" in report

    def test_report_has_timestamp(self):
        txt_file = SAMPLES / "sample.txt"
        if not txt_file.exists():
            pytest.skip("测试文件不存在")

        parsed = parse_paper(str(txt_file))
        report = generate_report(
            _mock_9d_all_pass(),
            parsed["metadata"]["title"],
            parsed["metadata"]["authors"],
        )
        # Timestamp in format YYYY-MM-DD HH:MM
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", report)
