"""
指标名归一化脚本

功能：
1. 读取 paper_data_points 中所有 metric_name
2. 使用 metric_normalizer 归一化为 canonical name
3. 回填 metric_name_normalized 字段

用法：
    python scripts/normalize_existing_metrics.py [--db PATH]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

import config
from db import get_connection
from phase3.metric_normalizer import normalize_metric_name
from logger import get_logger

logger = get_logger("normalize_metrics")


def normalize_all_metrics(db_path: str = None):
    """归一化所有已存在的指标名"""
    if db_path:
        config.SQLITE_PATH = Path(db_path)
    
    conn = get_connection(init_schema=False, row_factory=True)
    cur = conn.cursor()
    
    # 获取所有未归一化的数据点
    cur.execute("""
        SELECT id, metric_name 
        FROM paper_data_points 
        WHERE metric_name IS NOT NULL 
          AND metric_name != '' 
          AND metric_name_normalized IS NULL
    """)
    
    rows = cur.fetchall()
    logger.info(f"找到 {len(rows)} 条待归一化的指标记录")
    
    if not rows:
        logger.info("无需归一化")
        conn.close()
        return
    
    # 统计归一化结果
    normalized_count = 0
    unique_mappings = {}
    
    for row in rows:
        dp_id = row["id"]
        original_name = row["metric_name"]
        
        # 归一化
        normalized_name = normalize_metric_name(original_name)
        
        # 记录映射关系（用于统计）
        if original_name not in unique_mappings:
            unique_mappings[original_name] = normalized_name
        
        # 更新数据库
        conn.execute(
            "UPDATE paper_data_points SET metric_name_normalized = ? WHERE id = ?",
            (normalized_name, dp_id)
        )
        normalized_count += 1
    
    conn.commit()
    conn.close()
    
    # 输出统计
    logger.info("=" * 60)
    logger.info(f"归一化完成: 共处理 {normalized_count} 条记录")
    logger.info(f"唯一映射数: {len(unique_mappings)}")
    
    # 显示前 20 个映射示例
    logger.info("\n指标名映射示例（前 20 个）:")
    for i, (orig, norm) in enumerate(list(unique_mappings.items())[:20], 1):
        if orig != norm:
            logger.info(f"  {i}. '{orig}' → '{norm}'")
        else:
            logger.info(f"  {i}. '{orig}' (未变化)")
    
    return normalized_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="归一化指标名")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    args = parser.parse_args()
    
    normalize_all_metrics(db_path=args.db)
