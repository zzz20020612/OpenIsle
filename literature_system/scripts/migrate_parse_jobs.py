"""parse_jobs 表结构迁移脚本。

为已存在的数据库补充工作流审计所需字段与归档表：
- parse_jobs.parent_job_id
- parse_jobs_archive 表及索引

用法：
    python scripts/migrate_parse_jobs.py
    python scripts/migrate_parse_jobs.py --db path/to/literature.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "code"))

import config


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def migrate(conn: sqlite3.Connection) -> dict:
    """执行迁移，返回变更摘要。"""
    changes = {"added_parent_job_id": False, "created_archive": False}

    if not _table_exists(conn, "parse_jobs"):
        # 数据库尚未初始化到 parse_jobs，无需迁移
        return changes

    if not _column_exists(conn, "parse_jobs", "parent_job_id"):
        conn.execute("ALTER TABLE parse_jobs ADD COLUMN parent_job_id INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_parent ON parse_jobs(parent_job_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_error_class ON parse_jobs(error_class)"
        )
        changes["added_parent_job_id"] = True

    if not _table_exists(conn, "parse_jobs_archive"):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS parse_jobs_archive (
                id INTEGER PRIMARY KEY,
                paper_id INTEGER,
                stage TEXT,
                status TEXT,
                parser_used TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                parent_job_id INTEGER,
                error_class TEXT,
                error_msg TEXT,
                mineru_task_id TEXT,
                started_at TEXT,
                finished_at TEXT,
                archived_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_archive_status ON parse_jobs_archive(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_archive_paper ON parse_jobs_archive(paper_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_archive_archived ON parse_jobs_archive(archived_at);
            """
        )
        changes["created_archive"] = True

    conn.commit()
    return changes


def main():
    parser = argparse.ArgumentParser(description="迁移 parse_jobs 表结构")
    parser.add_argument("--db", type=Path, help="SQLite 数据库路径")
    args = parser.parse_args()

    db_path = args.db or config.SQLITE_PATH
    print(f"正在迁移: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        changes = migrate(conn)
        print(f"变更: {changes}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
