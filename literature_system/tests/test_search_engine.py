from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from search.engine import SearchEngine


class SearchAggregationTest(unittest.TestCase):
    def test_keyword_aggregate_uses_fts_table_name_for_match(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            "CREATE TABLE papers (id INTEGER PRIMARY KEY, journal_tier TEXT)"
        )
        connection.execute("INSERT INTO papers VALUES (1, 'tier1')")
        engine = SearchEngine(connection)
        engine.ensure_index()
        connection.execute(
            """INSERT INTO papers_fts
               (paper_id, title, abstract, keywords, authors, journal, full_text,
                published_year, language, source, doi)
               VALUES (1, 'Reproducible research', '', '', 'Ada', 'Test Journal',
                       '', '2024', 'en', 'crossref', '10.1/test')"""
        )

        result = engine.aggregate("research")

        self.assertEqual(1, result["journal_tier"][0]["count"])
        self.assertEqual("tier1", result["journal_tier"][0]["key"])

    def _content_engine(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            "CREATE TABLE papers (id INTEGER PRIMARY KEY, journal_tier TEXT)"
        )
        connection.execute(
            "CREATE TABLE paper_knowledge_cards (paper_id INTEGER PRIMARY KEY, core_answer TEXT)"
        )
        engine = SearchEngine(connection)
        engine.ensure_index()
        return connection, engine

    def test_search_uses_matching_fulltext_when_abstract_is_empty(self):
        connection, engine = self._content_engine()
        connection.execute("INSERT INTO papers VALUES (1, NULL)")
        connection.execute(
            """INSERT INTO papers_fts
               (paper_id, title, abstract, keywords, authors, journal, full_text,
                published_year, language, source, doi)
               VALUES (1, 'Parsed paper', '', '', '', 'Journal',
                       'A reproducibility result appears in the parsed PDF.',
                       '2024', 'en', 'crossref', '10.1/fulltext')"""
        )

        hit = engine.search("reproducibility")["hits"][0]

        self.assertIn("reproducibility", hit["abstract_snippet"].lower())
        self.assertEqual("fulltext", hit["snippet_source"])
        self.assertEqual("fulltext", hit["content_status"])

    def test_search_uses_knowledge_summary_for_unfiltered_results(self):
        connection, engine = self._content_engine()
        connection.execute("INSERT INTO papers VALUES (2, NULL)")
        connection.execute(
            "INSERT INTO paper_knowledge_cards VALUES (2, 'Structured knowledge summary')"
        )
        connection.execute(
            """INSERT INTO papers_fts
               (paper_id, title, abstract, keywords, authors, journal, full_text,
                published_year, language, source, doi)
               VALUES (2, 'Knowledge paper', '', '', '', 'Journal', 'Raw PDF header text',
                       '2024', 'en', 'crossref', '10.1/knowledge')"""
        )

        hit = engine.search("")["hits"][0]

        self.assertEqual("Structured knowledge summary", hit["abstract_snippet"])
        self.assertEqual("knowledge", hit["snippet_source"])
        self.assertEqual("knowledge", hit["content_status"])


if __name__ == "__main__":
    unittest.main()
