"""Tests for check_references.py — dim-08 参考文献检测。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_references import (
    _check_doi_format,
    _check_reference_format_consistency,
    _compute_self_citation_rate,
    _extract_references_section,
    _parse_references,
    check_references,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_paper(refs_text: str = "", authors: list | None = None) -> dict:
    segments = []
    if refs_text:
        segments.append({"type": "references", "text": refs_text})
    return {
        "metadata": {"title": "Test", "authors": authors or []},
        "segments": segments,
        "images": [],
        "tables": [],
    }


# ---------------------------------------------------------------------------
# DOI format
# ---------------------------------------------------------------------------

class TestDOIFormat:
    def test_valid_doi(self):
        refs = [{"doi": "10.1234/abc.def", "raw": "test"}]
        assert _check_doi_format(refs) == []

    def test_invalid_doi(self):
        refs = [{"doi": "invalid-doi", "raw": "test"}]
        issues = _check_doi_format(refs)
        assert len(issues) == 1

    def test_no_doi(self):
        refs = [{"doi": None, "raw": "test"}]
        assert _check_doi_format(refs) == []


# ---------------------------------------------------------------------------
# Self-citation
# ---------------------------------------------------------------------------

class TestSelfCitation:
    def test_no_authors(self):
        refs = [{"raw": "Smith 2020"}]
        assert _compute_self_citation_rate(refs, []) == 0.0

    def test_self_citation(self):
        refs = [{"raw": "Smith 2020"}, {"raw": "Jones 2021"}, {"raw": "Smith 2022"}]
        assert _compute_self_citation_rate(refs, ["Smith"]) == pytest.approx(2 / 3)

    def test_no_self_citation(self):
        refs = [{"raw": "Jones 2020"}, {"raw": "Brown 2021"}]
        assert _compute_self_citation_rate(refs, ["Smith"]) == 0.0


# ---------------------------------------------------------------------------
# Reference parsing
# ---------------------------------------------------------------------------

class TestParseReferences:
    def test_empty(self):
        assert _parse_references("") == []

    def test_numbered_refs(self):
        text = "[1] Smith 2020. doi: 10.1234/abc\n[2] Jones 2021. doi: 10.5678/def"
        refs = _parse_references(text)
        assert len(refs) == 2
        assert refs[0]["doi"] == "10.1234/abc"

    def test_extract_references_section(self):
        segments = [
            {"type": "body", "text": "Some body text"},
            {"type": "references", "text": "[1] Ref one"},
        ]
        text = _extract_references_section(segments)
        assert "Ref one" in text


# ---------------------------------------------------------------------------
# Format consistency
# ---------------------------------------------------------------------------

class TestFormatConsistency:
    def test_consistent(self):
        refs = [{"doi": "10.1/a"}, {"doi": "10.1/b"}, {"doi": "10.1/c"}]
        assert _check_reference_format_consistency(refs) == []

    def test_inconsistent(self):
        refs = [{"doi": None}, {"doi": None}, {"doi": None}, {"doi": "10.1/a"}]
        issues = _check_reference_format_consistency(refs)
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Full check
# ---------------------------------------------------------------------------

class TestCheckReferences:
    def test_empty_refs(self):
        paper = _make_paper()
        result = check_references(paper)
        assert result["dimension_id"] == "08"
        assert result["status"] in ("warning", "passed")  # 无参考文献 → at least minor finding

    def test_with_refs(self):
        refs = "[1] Smith 2020. doi: 10.1234/abc\n[2] Jones 2021. doi: 10.5678/def"
        paper = _make_paper(refs_text=refs, authors=["Smith"])
        result = check_references(paper)
        assert result["dimension_id"] == "08"
        assert "detail" in result

    def test_result_format(self):
        paper = _make_paper()
        result = check_references(paper)
        assert "dimension_id" in result
        assert "status" in result
        assert "findings" in result
