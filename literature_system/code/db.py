"""统一数据库连接模块。

消除原先分散在 7 个文件中的 get_connection 重复实现。
支持 SQLite（默认）和 PostgreSQL，可选是否自动初始化 schema、是否使用 Row 工厂。

使用示例：
    from db import get_connection

    # 默认：自动初始化 schema，使用普通 tuple
    conn = get_connection()

    # 不初始化 schema（查询时用），使用 Row 工厂
    conn = get_connection(init_schema=False, row_factory=True)

    # PostgreSQL
    conn = get_connection()  # 自动读取 config.DB_TYPE
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Optional

import config
from logger import get_logger

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = get_logger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "db_schema_sqlite.sql"


def get_connection(
    init_schema: bool = True,
    row_factory: bool = False,
    db_path: Optional[Path] = None,
):
    """获取数据库连接。

    Args:
        init_schema: 是否自动执行 schema 初始化（仅 SQLite 生效）。
                     首次建库或写入场景应 True；纯查询场景可 False 以加速。
        row_factory: 是否设置 sqlite3.Row 工厂（让 fetch 返回 dict-like 行）。
        db_path: 自定义 SQLite 路径，None 则用 config.SQLITE_PATH。

    Returns:
        sqlite3.Connection 或 psycopg2.connection
    """
    if config.DB_TYPE == "sqlite":
        path = db_path or config.SQLITE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        if row_factory:
            conn.row_factory = sqlite3.Row
        if init_schema:
            _init_sqlite_schema(conn)
        return conn

    # PostgreSQL
    import psycopg2  # 延迟导入，避免未安装时影响 SQLite 用户

    return psycopg2.connect(**config.DB_CONFIG)


def _init_sqlite_schema(conn: sqlite3.Connection) -> None:
    """执行 SQLite schema 初始化（CREATE TABLE IF NOT EXISTS，幂等）。"""
    try:
        if _SCHEMA_PATH.exists():
            schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
        else:
            logger.warning("未找到 db_schema_sqlite.sql 文件: %s", _SCHEMA_PATH)
        # 为旧数据库补充工作流审计字段与归档表
        try:
            from scripts.migrate_parse_jobs import migrate as _migrate_parse_jobs
            _migrate_parse_jobs(conn)
        except Exception as e:
            logger.error("parse_jobs 迁移失败: %s", e)
    except Exception as e:
        logger.error("执行 SQLite schema 初始化失败: %s", e)


def get_conn(row_factory: bool = True):
    """parse_scheduler 兼容别名。

    parse_scheduler.get_conn 原实现：不初始化 schema，使用 Row 工厂。
    供 pdf_pipeline / ref_parser / in_text_citations / citation_network / metadata_enhancer 使用。
    """
    return get_connection(init_schema=False, row_factory=row_factory)
