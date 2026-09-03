from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pytest


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from quality.completeness import assess_completeness, load_completeness_many


def complete_input(**overrides):
    payload = {
        "title": "A complete open paper",
        "author": "Alice Example, Bob Example",
        "doi": "10.1000/demo",
        "oa_url": "https://example.org/demo.pdf",
        "pdf_available": True,
        "fulltext_char_count": 12_000,
        "section_count": 6,
        "knowledge_present": True,
        "methods_present": True,
        "data_extraction_status": "done",
        "figure_count": 2,
        "latest_job": None,
    }
    payload.update(overrides)
    return payload


def test_complete_paper_passes_demo_audit():
    result = assess_completeness(complete_input())

    assert result["state"] == "complete"
    assert result["complete"] is True
    assert result["retryable"] is False
    assert result["reason_codes"] == []
    assert result["level"] == "L4"
    assert result["usable"] is True
    assert result["evaluable"] is True


@pytest.mark.parametrize(
    "overrides,expected_level",
    [
        ({"pdf_available": False}, "L0"),
        ({"fulltext_char_count": 0, "section_count": 0}, "L1"),
        ({"knowledge_present": False}, "L2"),
        ({"data_extraction_status": "failed"}, "L3"),
        ({"data_extraction_status": "skipped"}, "L4"),
    ],
)
def test_completeness_levels_follow_persisted_artifacts(overrides, expected_level):
    result = assess_completeness(complete_input(**overrides))

    assert result["level"] == expected_level
    assert result["usable"] is (expected_level in {"L2", "L3", "L4"})
    assert result["evaluable"] is (expected_level == "L4")


def test_missing_figures_are_reported_without_blocking_evaluation():
    result = assess_completeness(complete_input(figure_count=0))

    assert result["level"] == "L4"
    assert result["visual_content_extracted"] is False
    assert "visual_content_missing" in result["warnings"]


@pytest.mark.parametrize("missing_field", ["title", "author"])
def test_missing_required_metadata_is_incomplete(missing_field):
    result = assess_completeness(complete_input(**{missing_field: ""}))

    assert result["state"] == "incomplete"
    assert result["complete"] is False
    assert f"missing_{missing_field}" in result["reason_codes"]
    assert result["level"] == "L4"


def test_downloadable_but_not_downloaded_pdf_is_retryable():
    result = assess_completeness(complete_input(pdf_available=False))

    assert result["state"] == "retryable"
    assert result["retryable"] is True
    assert result["stage"] == "pdf"
    assert "pdf_not_downloaded" in result["reason_codes"]


def test_missing_pdf_identity_is_terminal():
    result = assess_completeness(
        complete_input(pdf_available=False, doi="", oa_url="")
    )

    assert result["state"] == "terminal"
    assert result["retryable"] is False
    assert "no_pdf_locator" in result["reason_codes"]


def test_short_fulltext_is_incomplete_and_retryable():
    result = assess_completeness(complete_input(fulltext_char_count=480))

    assert result["state"] == "incomplete"
    assert result["retryable"] is True
    assert result["stage"] == "parse"
    assert "fulltext_too_short" in result["reason_codes"]


def test_missing_knowledge_artifacts_are_retryable():
    result = assess_completeness(
        complete_input(knowledge_present=False, methods_present=False)
    )

    assert result["state"] == "retryable"
    assert result["stage"] == "extract"
    assert result["reason_codes"] == ["knowledge_missing", "methods_missing"]


def test_running_job_takes_precedence_over_missing_artifacts():
    result = assess_completeness(
        complete_input(
            knowledge_present=False,
            latest_job={"stage": "extract", "status": "running"},
        )
    )

    assert result["state"] == "processing"
    assert result["stage"] == "extract"
    assert result["retryable"] is False


@pytest.mark.parametrize(
    "error_class,error_message,expected_reason",
    [
        ("PaywallError", "publisher access requires payment", "paywalled"),
        ("InvalidPdfError", "downloaded payload is not a PDF", "invalid_pdf"),
        ("PaperMismatchError", "title does not match PDF", "paper_mismatch"),
    ],
)
def test_known_permanent_failures_are_terminal(
    error_class, error_message, expected_reason
):
    result = assess_completeness(
        complete_input(
            pdf_available=False,
            latest_job={
                "stage": "parse",
                "status": "permanent_failed",
                "error_class": error_class,
                "error_msg": error_message,
            },
        )
    )

    assert result["state"] == "terminal"
    assert result["retryable"] is False
    assert expected_reason in result["reason_codes"]


def test_database_loader_aggregates_artifacts_and_latest_job():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY, doi TEXT, title TEXT, author TEXT, oa_url TEXT
        );
        CREATE TABLE paper_fulltext (paper_id INTEGER PRIMARY KEY, char_count INTEGER);
        CREATE TABLE paper_sections (id INTEGER PRIMARY KEY, paper_id INTEGER);
        CREATE TABLE paper_knowledge_cards (paper_id INTEGER PRIMARY KEY);
        CREATE TABLE paper_methods (paper_id INTEGER PRIMARY KEY);
        CREATE TABLE paper_figures (id INTEGER PRIMARY KEY, paper_id INTEGER);
        CREATE TABLE parse_jobs (
            id INTEGER PRIMARY KEY, paper_id INTEGER, stage TEXT, status TEXT,
            parser_used TEXT, error_class TEXT, error_msg TEXT, created_at TEXT
        );
        INSERT INTO papers VALUES
            (1, '10.1/complete', 'Complete', 'Alice', 'https://oa/1.pdf'),
            (2, '10.1/failed', 'Failed', 'Bob', 'https://oa/2.pdf');
        INSERT INTO paper_fulltext VALUES (1, 12000);
        INSERT INTO paper_sections VALUES (1, 1), (2, 1);
        INSERT INTO paper_knowledge_cards VALUES (1);
        INSERT INTO paper_methods VALUES (1);
        INSERT INTO paper_figures VALUES (1, 1), (2, 1);
        INSERT INTO parse_jobs VALUES
            (1, 2, 'pdf', 'failed', NULL, 'NetworkError', 'timeout', '2026-08-21'),
            (2, 2, 'pdf', 'running', NULL, NULL, NULL, '2026-08-22'),
            (3, 1, 'extract', 'done', 'data_points', NULL, NULL, '2026-08-22');
        """
    )

    results = load_completeness_many(conn, [1, 2], {1: True, 2: False})

    assert results[1]["state"] == "complete"
    assert results[1]["level"] == "L4"
    assert results[1]["evidence"]["section_count"] == 2
    assert results[1]["evidence"]["figure_count"] == 2
    assert results[2]["state"] == "processing"
    assert results[2]["stage"] == "pdf"


def test_database_loader_returns_no_entry_for_unknown_paper():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY, doi TEXT, title TEXT, author TEXT, oa_url TEXT
        );
        CREATE TABLE paper_fulltext (paper_id INTEGER PRIMARY KEY, char_count INTEGER);
        CREATE TABLE paper_sections (id INTEGER PRIMARY KEY, paper_id INTEGER);
        CREATE TABLE paper_knowledge_cards (paper_id INTEGER PRIMARY KEY);
        CREATE TABLE paper_methods (paper_id INTEGER PRIMARY KEY);
        CREATE TABLE paper_figures (id INTEGER PRIMARY KEY, paper_id INTEGER);
        CREATE TABLE parse_jobs (
            id INTEGER PRIMARY KEY, paper_id INTEGER, stage TEXT, status TEXT,
            parser_used TEXT, error_class TEXT, error_msg TEXT, created_at TEXT
        );
        """
    )

    assert load_completeness_many(conn, [999], {999: False}) == {}
