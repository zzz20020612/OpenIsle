"""Tests for parse_paper module.

Tests verify real behavior against actual sample files (no mocks).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.parse_paper import _strip_latex, parse_paper

SAMPLES = Path(__file__).resolve().parent.parent / "test_samples"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _required_keys(result: dict) -> None:
    """Assert the top-level structure of a parse result."""
    assert set(result.keys()) == {"metadata", "segments", "images", "tables", "declarations"}
    assert isinstance(result["segments"], list)
    assert isinstance(result["images"], list)
    assert isinstance(result["tables"], list)
    assert isinstance(result["declarations"], dict)


def _metadata_keys(result: dict, expected_format: str) -> None:
    """Assert metadata contains all required fields."""
    m = result["metadata"]
    assert m["format"] == expected_format
    assert isinstance(m["title"], str)
    assert isinstance(m["authors"], list)
    assert isinstance(m["has_abstract"], bool)
    assert isinstance(m["page_count"], int)
    assert isinstance(m["file_size_bytes"], int)
    assert m["page_count"] >= 1
    assert m["file_size_bytes"] > 0


def _segment_keys(seg: dict) -> None:
    """Assert a segment has the required fields."""
    assert "type" in seg
    assert "text" in seg
    assert "page_start" in seg
    assert "page_end" in seg
    assert "confidence" in seg
    assert isinstance(seg["text"], str)
    assert len(seg["text"]) > 0
    assert 0.0 <= seg["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_paper("/nonexistent/path/paper.pdf")

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"data")
            f.flush()
            with pytest.raises(ValueError, match="Unsupported"):
                parse_paper(f.name)

    def test_empty_file_name_rejected(self):
        with pytest.raises((FileNotFoundError, ValueError)):
            parse_paper("")


# ---------------------------------------------------------------------------
# TXT parsing
# ---------------------------------------------------------------------------

class TestParseTxt:
    SAMPLE = SAMPLES / "sample.txt"

    def test_metadata_structure(self):
        result = parse_paper(str(self.SAMPLE))
        _required_keys(result)
        _metadata_keys(result, "txt")

    def test_has_abstract_flag(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["has_abstract"] is True

    def test_title_extracted(self):
        result = parse_paper(str(self.SAMPLE))
        assert "Machine Learning" in result["metadata"]["title"]

    def test_segments_not_empty(self):
        result = parse_paper(str(self.SAMPLE))
        assert len(result["segments"]) > 0

    def test_segment_fields(self):
        result = parse_paper(str(self.SAMPLE))
        for seg in result["segments"]:
            _segment_keys(seg)

    def test_section_detection(self):
        result = parse_paper(str(self.SAMPLE))
        types = [s["type"] for s in result["segments"]]
        assert "abstract" in types
        assert "introduction" in types
        assert "methods" in types
        assert "results" in types
        assert "conclusion" in types
        assert "references" in types

    def test_page_count_is_one(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["page_count"] == 1

    def test_file_size_matches(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["file_size_bytes"] == self.SAMPLE.stat().st_size

    def test_images_tables_empty(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["images"] == []
        assert result["tables"] == []


# ---------------------------------------------------------------------------
# DOCX parsing
# ---------------------------------------------------------------------------

class TestParseDocx:
    SAMPLE = SAMPLES / "sample.docx"

    def test_metadata_structure(self):
        result = parse_paper(str(self.SAMPLE))
        _required_keys(result)
        _metadata_keys(result, "docx")

    def test_title_from_core_properties(self):
        result = parse_paper(str(self.SAMPLE))
        assert "Reinforcement Learning" in result["metadata"]["title"]

    def test_authors_extracted(self):
        result = parse_paper(str(self.SAMPLE))
        assert len(result["metadata"]["authors"]) > 0

    def test_has_abstract(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["has_abstract"] is True

    def test_segments_not_empty(self):
        result = parse_paper(str(self.SAMPLE))
        assert len(result["segments"]) > 0

    def test_section_detection(self):
        result = parse_paper(str(self.SAMPLE))
        types = [s["type"] for s in result["segments"]]
        assert "abstract" in types
        assert "introduction" in types
        assert "conclusion" in types


# ---------------------------------------------------------------------------
# PDF parsing
# ---------------------------------------------------------------------------

class TestParsePdf:
    SAMPLE = SAMPLES / "sample.pdf"

    def test_metadata_structure(self):
        result = parse_paper(str(self.SAMPLE))
        _required_keys(result)
        _metadata_keys(result, "pdf")

    def test_page_count(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["page_count"] >= 1

    def test_has_abstract(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["has_abstract"] is True

    def test_segments_not_empty(self):
        result = parse_paper(str(self.SAMPLE))
        assert len(result["segments"]) > 0

    def test_segments_have_text(self):
        result = parse_paper(str(self.SAMPLE))
        for seg in result["segments"]:
            assert len(seg["text"]) > 0


# ---------------------------------------------------------------------------
# LaTeX parsing
# ---------------------------------------------------------------------------

class TestParseTex:
    SAMPLE = SAMPLES / "sample.tex"

    def test_metadata_structure(self):
        result = parse_paper(str(self.SAMPLE))
        _required_keys(result)
        _metadata_keys(result, "tex")

    def test_title_extracted(self):
        result = parse_paper(str(self.SAMPLE))
        assert "Transformer" in result["metadata"]["title"]

    def test_authors_extracted(self):
        result = parse_paper(str(self.SAMPLE))
        authors = result["metadata"]["authors"]
        assert len(authors) == 3
        assert "Alice Johnson" in authors
        assert "Bob Williams" in authors

    def test_has_abstract(self):
        result = parse_paper(str(self.SAMPLE))
        assert result["metadata"]["has_abstract"] is True

    def test_segments_not_empty(self):
        result = parse_paper(str(self.SAMPLE))
        assert len(result["segments"]) > 0

    def test_latex_commands_stripped(self):
        result = parse_paper(str(self.SAMPLE))
        for seg in result["segments"]:
            assert "\\section" not in seg["text"]
            assert "\\begin" not in seg["text"]

    def test_section_detection(self):
        result = parse_paper(str(self.SAMPLE))
        types = [s["type"] for s in result["segments"]]
        assert "abstract" in types
        assert "introduction" in types


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_plain_text_no_sections(self):
        """A plain text file with no section headings should produce body segments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("This is just a plain paragraph.\n\nAnd another one here.")
            f.flush()
            result = parse_paper(f.name)

        assert result["metadata"]["format"] == "txt"
        assert len(result["segments"]) >= 2
        assert all(s["type"] == "body" for s in result["segments"])

    def test_title_first_line(self):
        """Title should be the first non-empty line of the file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n\n\n  My Paper Title  \nContent here.")
            f.flush()
            result = parse_paper(f.name)

        assert result["metadata"]["title"] == "My Paper Title"

    def test_txt_no_abstract(self):
        """A file without 'abstract' keyword should have has_abstract=False."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Just some text without any special heading.\n\nMore text here.")
            f.flush()
            result = parse_paper(f.name)

        assert result["metadata"]["has_abstract"] is False

    def test_long_text_truncated(self):
        """Segments should be capped at 5000 chars."""
        long_text = "x" * 6000
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(long_text)
            f.flush()
            result = parse_paper(f.name)

        for seg in result["segments"]:
            assert len(seg["text"]) <= 5000


# ---------------------------------------------------------------------------
# _strip_latex unit tests
# ---------------------------------------------------------------------------

class TestStripLatex:
    def test_nested_commands(self):
        assert _strip_latex(r"\textbf{\textit{nested}}") == "nested"

    def test_simple_command(self):
        assert _strip_latex(r"\emph{word}") == "word"

    def test_standalone_command(self):
        assert _strip_latex(r"\centering") == ""

    def test_tilde_replaced(self):
        assert _strip_latex(r"a~b") == "a b"

    def test_triple_nested(self):
        assert _strip_latex(r"\textbf{\textit{\underline{deep}}}") == "deep"
