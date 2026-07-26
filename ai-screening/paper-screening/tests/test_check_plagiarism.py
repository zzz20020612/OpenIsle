"""Tests for check_plagiarism.py — dim-02 重复文本检测。"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_plagiarism import (
    _compute_similarity,
    _extract_abstract,
    _extract_section,
    _ngrams,
    _reconstruct_abstract,
    check_plagiarism,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_paper(abstract: str = "", methods: str = "", results: str = "") -> dict:
    segments = []
    if abstract:
        segments.append({"type": "abstract", "text": abstract})
    if methods:
        segments.append({"type": "methods", "text": methods})
    if results:
        segments.append({"type": "results", "text": results})
    return {"metadata": {"title": "Test"}, "segments": segments, "images": [], "tables": []}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

class TestTextExtraction:
    def test_extract_abstract(self):
        paper = _make_paper(abstract="This is the abstract.")
        assert _extract_abstract(paper["segments"]) == "This is the abstract."

    def test_extract_abstract_missing(self):
        assert _extract_abstract([]) == ""

    def test_extract_section(self):
        paper = _make_paper(methods="We used method X.")
        text = _extract_section(paper["segments"], "methods")
        assert "method X" in text

    def test_extract_section_empty(self):
        assert _extract_section([], "methods") == ""


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

class TestSimilarity:
    def test_identical_texts(self):
        assert _compute_similarity("the cat sat on the mat", "the cat sat on the mat") == 1.0

    def test_empty_texts(self):
        assert _compute_similarity("", "hello") == 0.0
        assert _compute_similarity("hello", "") == 0.0
        assert _compute_similarity("", "") == 0.0

    def test_similar_texts(self):
        # 1 word difference out of many → high Jaccard on word trigrams
        sim = _compute_similarity(
            "the quick brown fox jumps over the very lazy dog",
            "the quick brown fox jumps over the very lazy dogs",
        )
        assert sim > 0.4

    def test_different_texts(self):
        sim = _compute_similarity("cats are cute", "quantum physics is complex")
        assert sim < 0.3

    def test_ngrams(self):
        grams = _ngrams("a b c d", 2)
        assert "a b" in grams
        assert "b c" in grams
        assert "c d" in grams


# ---------------------------------------------------------------------------
# OpenAlex abstract reconstruction
# ---------------------------------------------------------------------------

class TestOpenAlexAbstract:
    def test_reconstruct(self):
        inverted = {"the": [0], "cat": [1], "sat": [2]}
        assert _reconstruct_abstract(inverted) == "the cat sat"

    def test_reconstruct_empty(self):
        assert _reconstruct_abstract({}) == ""
    def test_reconstruct_none(self):
        assert _reconstruct_abstract(None) == ""


# ---------------------------------------------------------------------------
# Full check (mocked APIs)
# ---------------------------------------------------------------------------

class TestCheckPlagiarism:
    def test_empty_paper(self):
        paper = _make_paper()
        result = check_plagiarism(paper)
        assert result["dimension_id"] == "02"
        assert result["status"] == "passed"

    def test_with_abstract(self):
        paper = _make_paper(abstract="Machine learning is a subset of AI.")
        # Mock all API calls to return empty
        with patch("check_plagiarism._query_all_apis", return_value=[]):
            result = check_plagiarism(paper)
        assert result["dimension_id"] == "02"
        assert result["status"] in ("passed", "warning", "failed")

    def test_result_format(self):
        paper = _make_paper(abstract="Test abstract.")
        with patch("check_plagiarism._query_all_apis", return_value=[]):
            result = check_plagiarism(paper)
        assert "dimension_id" in result
        assert "status" in result
        assert "severity" in result
        assert "findings" in result
        assert "interaction_needed" in result
