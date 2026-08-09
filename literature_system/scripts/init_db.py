#!/usr/bin/env python3
"""
数据库一键初始化脚本

用法:
  python scripts/init_db.py              # 初始化 SQLite 数据库
  python scripts/init_db.py --demo       # 初始化并加载示例数据
  python scripts/init_db.py --postgres   # 初始化 PostgreSQL 数据库（需先配置 config/.env）
"""

import os
import sys
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "code"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / "config" / ".env")


def init_sqlite():
    """初始化 SQLite 数据库"""
    db_dir = ROOT_DIR / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    # 运行建表脚本
    sys.path.insert(0, str(db_dir))
    from apply_schema_sqlite import main as apply_schema
    apply_schema()
    print("[OK] SQLite 数据库初始化完成")


def init_postgres():
    """初始化 PostgreSQL 数据库"""
    db_dir = ROOT_DIR / "db"
    sys.path.insert(0, str(db_dir))
    from apply_schema import main as apply_schema
    apply_schema()
    print("[OK] PostgreSQL 数据库初始化完成")


def load_demo_data():
    """加载示例数据"""
    print("正在加载示例数据...")
    demo_script = ROOT_DIR / "scripts" / "load_demo_data.py"
    if demo_script.exists():
        # 动态导入
        import importlib.util
        spec = importlib.util.spec_from_file_location("load_demo_data", demo_script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
    else:
        print("[WARN] 未找到示例数据脚本 scripts/load_demo_data.py")
    print("[OK] 示例数据加载完成")


def main():
    parser = argparse.ArgumentParser(description="文献系统数据库初始化")
    parser.add_argument("--demo", action="store_true", help="同时加载示例数据")
    parser.add_argument("--postgres", action="store_true", help="使用 PostgreSQL（默认 SQLite）")
    args = parser.parse_args()

    if args.postgres:
        init_postgres()
    else:
        init_sqlite()

    if args.demo:
        load_demo_data()

    print("\n数据库初始化完成！")
    print("下一步：")
    print("  1. 编辑 config/.env 配置 API Key")
    print("  2. 启动服务: python code/search/api.py")
    print("  3. 访问 http://localhost:8088")


if __name__ == "__main__":
    main()