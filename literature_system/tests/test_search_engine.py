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


if __name__ == "__main__":
    unittest.main()
