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

from phase3 import job_tracker


class ExtractionJobTrackerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directory.name) / "jobs.db"
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """CREATE TABLE parse_jobs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 paper_id INTEGER,
                 stage TEXT,
                 status TEXT,
                 parser_used TEXT,
                 retry_count INTEGER DEFAULT 0,
                 max_retries INTEGER DEFAULT 3,
                 parent_job_id INTEGER,
                 error_class TEXT,
                 error_msg TEXT,
                 started_at TEXT,
                 finished_at TEXT,
                 created_at TEXT,
                 updated_at TEXT
               )"""
        )
        connection.close()

    def tearDown(self):
        self.directory.cleanup()

    def open_connection(self, *args, **kwargs):
        connection = sqlite3.connect(self.db_path)
        if kwargs.get("row_factory"):
            connection.row_factory = sqlite3.Row
        return connection

    def test_terminal_state_closes_latest_running_job(self):
        with patch.object(job_tracker, "get_connection", side_effect=self.open_connection):
            job_tracker.record_extraction_status(8, "knowledge_card", "running")
            job_tracker.record_extraction_status(8, "knowledge_card", "done")

        connection = sqlite3.connect(self.db_path)
        rows = connection.execute(
            "SELECT status FROM parse_jobs WHERE paper_id=8 AND parser_used='knowledge_card'"
        ).fetchall()
        connection.close()
        self.assertEqual([("done",)], rows)

    def test_terminal_state_without_running_job_is_inserted(self):
        with patch.object(job_tracker, "get_connection", side_effect=self.open_connection):
            job_tracker.record_extraction_status(10, "methods", "failed", error_msg="bad output")

        connection = sqlite3.connect(self.db_path)
        row = connection.execute(
            "SELECT status, error_msg FROM parse_jobs WHERE paper_id=10 AND parser_used='methods'"
        ).fetchone()
        connection.close()
        self.assertEqual(("failed", "bad output"), row)

    def test_legacy_running_row_with_newer_terminal_record_is_superseded(self):
        connection = sqlite3.connect(self.db_path)
        connection.executemany(
            """INSERT INTO parse_jobs
               (paper_id, stage, status, parser_used, started_at, finished_at)
               VALUES (8, 'extract', ?, 'knowledge_card', '2026-01-01', '2026-01-01')""",
            [("running",), ("done",)],
        )
        connection.commit()
        connection.close()

        with patch.object(job_tracker, "get_connection", side_effect=self.open_connection):
            changed = job_tracker.reset_stale_running_jobs()

        connection = sqlite3.connect(self.db_path)
        statuses = [
            row[0]
            for row in connection.execute("SELECT status FROM parse_jobs ORDER BY id")
        ]
        connection.close()
        self.assertEqual(1, changed)
        self.assertEqual(["superseded", "done"], statuses)


if __name__ == "__main__":
    unittest.main()
