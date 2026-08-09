from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

import parse_new_papers


class PipelineScopeTest(unittest.TestCase):
    def test_parse_selection_only_uses_current_collection_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "scope.db"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE papers (
                    id INTEGER PRIMARY KEY,
                    doi TEXT,
                    title TEXT,
                    oa_url TEXT,
                    source TEXT
                );
                CREATE TABLE paper_fulltext (paper_id INTEGER PRIMARY KEY);
                INSERT INTO papers VALUES (1, '10.1/old', 'Old backlog', '', 'crossref');
                INSERT INTO papers VALUES (2, '10.1/done', 'Already parsed', '', 'crossref');
                INSERT INTO papers VALUES (3, '10.1/new', 'Current batch', '', 'crossref');
                INSERT INTO paper_fulltext VALUES (2);
                """
            )
            connection.commit()
            connection.close()

            def open_connection(*args, **kwargs):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                return conn

            with patch.object(parse_new_papers, "get_connection", side_effect=open_connection):
                papers = parse_new_papers.get_new_papers_with_oa(
                    limit=10,
                    source_prefer="all",
                    paper_ids=[2, 3],
                )

            self.assertEqual([3], [paper["id"] for paper in papers])


if __name__ == "__main__":
    unittest.main()
