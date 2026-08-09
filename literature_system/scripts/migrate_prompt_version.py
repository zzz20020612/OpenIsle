#!/usr/bin/env python3
"""
数据库迁移脚本：为 paper_knowledge_cards 表添加 prompt_version 字段

功能：
1. 检查 paper_knowledge_cards 表是否存在 prompt_version 字段
2. 如果不存在，则添加该字段
3. 为现有记录填充默认版本号

使用方法：
    python scripts/migrate_prompt_version.py
"""
import sys
from pathlib import Path

# 添加 code 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from db import get_connection
from logger import get_logger

logger = get_logger(__name__)


def migrate_prompt_version():
    """执行 prompt_version 字段迁移"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 检查字段是否存在
        cursor.execute("PRAGMA table_info(paper_knowledge_cards)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "prompt_version" in columns:
            logger.info("prompt_version 字段已存在，无需迁移")
            return
        
        logger.info("开始添加 prompt_version 字段...")
        
        # 添加字段
        cursor.execute("""
            ALTER TABLE paper_knowledge_cards 
            ADD COLUMN prompt_version TEXT DEFAULT 'v1'
        """)
        
        # 为现有记录填充默认版本号
        cursor.execute("""
            UPDATE paper_knowledge_cards 
            SET prompt_version = 'v1' 
            WHERE prompt_version IS NULL
        """)
        
        conn.commit()
        updated_count = cursor.rowcount
        
        logger.info(f"迁移完成：已更新 {updated_count} 条记录")
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_prompt_version()
