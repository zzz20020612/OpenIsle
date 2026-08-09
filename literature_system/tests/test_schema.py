from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path


class SchemaTest(unittest.TestCase):
    def test_schema_contains_pipeline_and_extraction_columns(self):
        schema_path = Path(__file__).resolve().parents[1] / "db" / "db_schema_sqlite.sql"
        connection = sqlite3.connect(":memory:")
        try:
            connection.executescript(schema_path.read_text(encoding="utf-8"))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertTrue(
                {
                    "papers",
                    "paper_fulltext",
                    "paper_sections",
                    "paper_knowledge_cards",
                    "paper_methods",
                    "paper_data_points",
                    "parse_jobs",
                }.issubset(tables)
            )
            job_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(parse_jobs)")
            }
            self.assertTrue(
                {"stage", "status", "retry_count", "error_class", "error_msg"}.issubset(job_columns)
            )
            fulltext_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(paper_fulltext)")
            }
            self.assertIn("full_markdown", fulltext_columns)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
