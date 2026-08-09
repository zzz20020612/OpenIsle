"""迁移 paper_data_points.metric_value 字段。

历史问题：
1. 13 条 paper_id=73 记录的 metric_value / *_numeric / *_original 全为 NULL：
   LLM 抽取时返回了 metric_name 但 metric_value 字段未填。
2. 10 条记录的 metric_value_original 有值但 metric_value_numeric 为 NULL：
   旧版 extractor 落库时未调用 parse_metric_value。

修复策略：
- 类型 1（13 条全空）：写入哨兵字符串 `unparseable`，prompt 修订后下次重抽可正确处理。
- 类型 2（10 条缺 numeric）：重新调用 parse_metric_value 解析 metric_value_original，
  若能解析则回填 metric_value_numeric。

用法：
    python scripts/migrate_data_points_value_type.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加 code 目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from logger import get_logger
from phase3.metric_normalizer import parse_metric_value

logger = get_logger("scripts.migrate_data_points_value_type")

UNPARSEABLE_SENTINEL = "unparseable"


def migrate(dry_run: bool = False) -> dict:
    """执行迁移。

    Args:
        dry_run: 仅打印，不实际更新

    Returns:
        迁移统计信息
    """
    stats = {
        "type1_null_records": 0,  # 13 条
        "type1_marked": 0,
        "type2_missing_numeric": 0,  # 10 条
        "type2_refilled": 0,
        "type2_unparseable": 0,
    }

    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()

        # ---- 类型 1：全空记录（13 条）----
        cur.execute("""
            SELECT dp.id, dp.paper_id, dp.metric_name, dp.metric_value
            FROM paper_data_points dp
            WHERE (dp.metric_value IS NULL OR dp.metric_value = '')
              AND (dp.metric_value_numeric IS NULL)
              AND (dp.metric_value_original IS NULL OR dp.metric_value_original = '')
        """)
        type1_rows = cur.fetchall()
        stats["type1_null_records"] = len(type1_rows)
        logger.info(f"类型 1（全空）: {len(type1_rows)} 条")

        for row in type1_rows:
            row_id = row["id"]
            paper_id = row["paper_id"]
            metric_name = (row["metric_name"] or "")[:50]
            logger.info(
                f"  [类型 1] id={row_id} paper={paper_id} metric={metric_name} → 标记 {UNPARSEABLE_SENTINEL!r}"
            )
            if not dry_run:
                # 写入哨兵字符串到 metric_value 字段（TEXT 类型），并保留 metric_name 用于追溯
                conn.execute(
                    """UPDATE paper_data_points
                       SET metric_value = ?,
                           metric_value_original = ?,
                           metric_value_numeric = NULL
                       WHERE id = ?""",
                    (UNPARSEABLE_SENTINEL, UNPARSEABLE_SENTINEL, row_id),
                )
                conn.commit()
                stats["type1_marked"] += 1

        # ---- 类型 2：原文存在但 numeric 为空（10 条）----
        cur.execute("""
            SELECT dp.id, dp.paper_id, dp.metric_name,
                   dp.metric_value, dp.metric_value_original
            FROM paper_data_points dp
            WHERE dp.metric_value_numeric IS NULL
              AND dp.metric_value_original IS NOT NULL
              AND dp.metric_value_original != ''
        """)
        type2_rows = cur.fetchall()
        stats["type2_missing_numeric"] = len(type2_rows)
        logger.info(f"类型 2（缺 numeric）: {len(type2_rows)} 条")

        for row in type2_rows:
            row_id = row["id"]
            paper_id = row["paper_id"]
            metric_name = (row["metric_name"] or "")[:30]
            raw_value = row["metric_value"]
            orig_value = row["metric_value_original"]

            # 用 parse_metric_value 重新解析（优先用 metric_value，回退到 original）
            source = raw_value if raw_value not in (None, "") else orig_value
            numeric, original = parse_metric_value(source)

            if numeric is not None:
                logger.info(
                    f"  [类型 2] id={row_id} paper={paper_id} metric={metric_name} "
                    f"{source!r} → numeric={numeric}"
                )
                if not dry_run:
                    conn.execute(
                        "UPDATE paper_data_points SET metric_value_numeric = ? WHERE id = ?",
                        (numeric, row_id),
                    )
                    conn.commit()
                    stats["type2_refilled"] += 1
            else:
                # 仍无法解析（如 "Y0" 是星等分类，不是数值）
                logger.info(
                    f"  [类型 2] id={row_id} paper={paper_id} metric={metric_name} "
                    f"{source!r} → 无法解析（哨兵）"
                )
                if not dry_run:
                    conn.execute(
                        "UPDATE paper_data_points SET metric_value_numeric = NULL WHERE id = ?",
                        (row_id,),
                    )
                    conn.commit()
                    stats["type2_unparseable"] += 1

        logger.info(
            f"迁移{'[DRY-RUN] ' if dry_run else ''}完成："
            f"类型 1 标记 {stats['type1_marked']}/{stats['type1_null_records']}；"
            f"类型 2 回填 {stats['type2_refilled']}，仍无法解析 {stats['type2_unparseable']}"
        )

    finally:
        conn.close()

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="迁移 paper_data_points.metric_value 字段"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不实际更新")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
