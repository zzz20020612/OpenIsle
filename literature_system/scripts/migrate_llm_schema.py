"""
数据库迁移脚本：LLM 优化相关 schema 变更

1. papers 表新增 is_placeholder 字段
2. paper_data_points 表：
   - metric_value 从 REAL 改为 TEXT（SQLite 动态类型，只需加新列）
   - 新增 metric_value_numeric / metric_value_original / metric_name_normalized
3. 回填历史数据：将 metric_value 中的数值写入 metric_value_numeric

用法：
    python scripts/migrate_llm_schema.py [--db PATH]
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
import config


def migrate(db_path: str = None):
    db_path = db_path or str(config.SQLITE_PATH)
    print(f"迁移数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. papers 表新增 is_placeholder
    cur.execute("PRAGMA table_info(papers)")
    paper_cols = {row[1] for row in cur.fetchall()}
    if "is_placeholder" not in paper_cols:
        cur.execute("ALTER TABLE papers ADD COLUMN is_placeholder INTEGER DEFAULT 0")
        print("  ✅ papers.is_placeholder 已添加")
    else:
        print("  ⏭️  papers.is_placeholder 已存在，跳过")

    # 2. paper_data_points 表新增列
    cur.execute("PRAGMA table_info(paper_data_points)")
    dp_cols = {row[1] for row in cur.fetchall()}

    new_cols = {
        "metric_value_numeric": "REAL",
        "metric_value_original": "TEXT",
        "metric_name_normalized": "TEXT",
    }
    for col_name, col_type in new_cols.items():
        if col_name not in dp_cols:
            cur.execute(f"ALTER TABLE paper_data_points ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ paper_data_points.{col_name} 已添加")
        else:
            print(f"  ⏭️  paper_data_points.{col_name} 已存在，跳过")

    conn.commit()

    # 3. 回填历史数据：将 metric_value 中的数值提取到 metric_value_numeric
    cur.execute(
        "SELECT id, metric_value FROM paper_data_points "
        "WHERE metric_value IS NOT NULL AND metric_value != '' "
        "AND metric_value_numeric IS NULL"
    )
    rows = cur.fetchall()
    updated = 0
    for row_id, val in rows:
        numeric, original = _parse_metric_value(val)
        if numeric is not None:
            cur.execute(
                "UPDATE paper_data_points SET metric_value_numeric=?, metric_value_original=? WHERE id=?",
                (numeric, original, row_id),
            )
        elif original:
            cur.execute(
                "UPDATE paper_data_points SET metric_value_original=? WHERE id=?",
                (original, row_id),
            )
        updated += 1

    conn.commit()
    print(f"  📊 回填 {updated} 条 paper_data_points 记录")

    conn.close()
    print("✅ 迁移完成")


def _parse_metric_value(val) -> tuple:
    """尝试从 metric_value 中提取数值。

    Returns:
        (numeric_value, original_text)
        numeric_value: float 或 None
        original_text: 原始文本（如果无法解析为单一数值）
    """
    if val is None:
        return None, None
    if isinstance(val, (int, float)):
        return float(val), None

    val_str = str(val).strip()
    if not val_str:
        return None, None

    # 尝试直接解析为数值
    try:
        return float(val_str), None
    except ValueError:
        pass

    # 尝试提取范围中的第一个数值（如 "50 to 150" → 50）
    m = re.match(r"([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)", val_str)
    if m:
        try:
            return float(m.group(1)), val_str
        except ValueError:
            pass

    # 无法解析为数值，保留原始文本
    return None, val_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="迁移 LLM 优化相关 schema")
    parser.add_argument("--db", type=str, default=None, help="数据库路径（默认使用 config.SQLITE_PATH）")
    args = parser.parse_args()
    migrate(args.db)
