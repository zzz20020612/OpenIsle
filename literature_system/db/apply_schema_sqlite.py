from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "code"))

import config


def main() -> None:
    config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("db_schema_sqlite.sql")
    schema = schema_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(config.SQLITE_PATH)
    try:
        connection.executescript(schema)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()

