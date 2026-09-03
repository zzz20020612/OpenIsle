from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from search.api import SearchAPIHandler


def _handler(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE papers (
          id INTEGER PRIMARY KEY, doi TEXT, title TEXT, published_date TEXT,
          journal TEXT, author TEXT, keywords TEXT, source TEXT,
          citation_count INTEGER, language TEXT, journal_tier TEXT, oa_url TEXT,
          is_placeholder INTEGER DEFAULT 0
        );
        CREATE TABLE paper_fulltext (paper_id INTEGER PRIMARY KEY, char_count INTEGER);
        CREATE TABLE paper_sections (id INTEGER PRIMARY KEY, paper_id INTEGER, content TEXT);
        CREATE TABLE paper_knowledge_cards (paper_id INTEGER PRIMARY KEY);
        CREATE TABLE paper_methods (paper_id INTEGER PRIMARY KEY);
        CREATE TABLE paper_figures (id INTEGER PRIMARY KEY, paper_id INTEGER);
        CREATE TABLE parse_jobs (
          id INTEGER PRIMARY KEY, paper_id INTEGER, stage TEXT, status TEXT,
          parser_used TEXT, error_class TEXT, error_msg TEXT
        );
        INSERT INTO papers
          (id, doi, title, published_date, journal, author, keywords, source,
           citation_count, language, journal_tier, oa_url)
        VALUES
          (1, '10.1/one', 'Metadata', '2024', 'J', '["A"]', '[]', 'pmc', 0, 'en', NULL, 'https://oa/1'),
          (2, '10.1/two', 'PDF', '2024', 'J', '["A"]', '[]', 'pmc', 0, 'en', NULL, 'https://oa/2'),
          (3, '10.1/three', 'Parsed', '2024', 'J', '["A"]', '[]', 'pmc', 0, 'en', NULL, 'https://oa/3'),
          (4, '10.1/four', 'Knowledge', '2024', 'J', '["A"]', '[]', 'pmc', 0, 'en', NULL, 'https://oa/4'),
          (5, '10.1/five', 'Evaluable', '2024', 'J', '["A"]', '[]', 'pmc', 0, 'en', NULL, 'https://oa/5');
        INSERT INTO paper_fulltext VALUES (3, 5000), (4, 5000), (5, 5000);
        INSERT INTO paper_sections VALUES (1, 3, 'Body'), (2, 4, 'Body'), (3, 5, 'Body');
        INSERT INTO paper_knowledge_cards VALUES (4), (5);
        INSERT INTO paper_methods VALUES (4), (5);
        INSERT INTO parse_jobs VALUES
          (1, 4, 'extract', 'failed', 'data_points', 'LLMError', 'bad json'),
          (2, 5, 'extract', 'skipped', 'data_points', NULL, 'not applicable');
        """
    )
    monkeypatch.setattr(
        "pdf.pipeline.get_pdf_path",
        lambda paper_id, doi=None: None if paper_id == 1 else Path(f"/{paper_id}.pdf"),
    )
    handler = SearchAPIHandler.__new__(SearchAPIHandler)
    handler.engine = SimpleNamespace(conn=connection)
    return handler


def test_usable_view_only_returns_parsed_levels(monkeypatch):
    result = _handler(monkeypatch)._handle_papers_list({"view": ["usable"]})

    assert result["total"] == 3
    assert {row["completeness"]["level"] for row in result["papers"]} == {"L2", "L3", "L4"}


def test_pending_view_returns_metadata_and_pdf_only(monkeypatch):
    result = _handler(monkeypatch)._handle_papers_list({"view": ["pending"]})

    assert result["total"] == 2
    assert {row["completeness"]["level"] for row in result["papers"]} == {"L0", "L1"}


def test_exact_file_backed_levels_have_correct_totals(monkeypatch):
    handler = _handler(monkeypatch)

    metadata = handler._handle_papers_list({"level": ["L0"]})
    pdf_ready = handler._handle_papers_list({"level": ["L1"]})

    assert metadata["total"] == 1
    assert metadata["papers"][0]["id"] == 1
    assert pdf_ready["total"] == 1
    assert pdf_ready["papers"][0]["id"] == 2


def test_exact_level_overrides_conflicting_admission_view(monkeypatch):
    result = _handler(monkeypatch)._handle_papers_list(
        {"view": ["usable"], "level": ["L0"]}
    )

    assert result["total"] == 1
    assert [row["completeness"]["level"] for row in result["papers"]] == ["L0"]
