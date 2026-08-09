from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from collect.multi_source_collector import find_missing_authors


class CollectorAuthorScopeTest(unittest.TestCase):
    def test_missing_author_lookup_can_be_limited_to_new_papers(self):
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE papers (id INTEGER PRIMARY KEY, doi TEXT, author TEXT)"
        )
        connection.executemany(
            "INSERT INTO papers VALUES (?, ?, ?)",
            [(1, "10.1/legacy", ""), (2, "10.1/new", ""), (3, "10.1/ready", "Ada")],
        )

        rows = find_missing_authors(connection, paper_ids=[2, 3])

        self.assertEqual([("10.1/new", 2)], rows)


if __name__ == "__main__":
    unittest.main()
