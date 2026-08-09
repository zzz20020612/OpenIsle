from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "code"))

import config


def ensure_compatibility(connection: sqlite3.Connection) -> None:
    """Add columns required by newer parsers to an existing SQLite database."""
    citation_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(citations_v2)")
    }
    if citation_columns and "cited_journal" not in citation_columns:
        connection.execute("ALTER TABLE citations_v2 ADD COLUMN cited_journal TEXT")


def main() -> None:
    config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("db_schema_sqlite.sql")
    schema = schema_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(config.SQLITE_PATH)
    try:
        connection.executescript(schema)
        ensure_compatibility(connection)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
