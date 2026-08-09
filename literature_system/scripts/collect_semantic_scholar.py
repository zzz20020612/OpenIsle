"""Semantic Scholar 采集入库脚本。

用法:
    python scripts/collect_semantic_scholar.py --keyword biowaste --target 10
"""
import sys
from pathlib import Path

# 确保能导入 code/ 目录下的模块
_CODE_ROOT = Path(__file__).resolve().parent.parent / "code"
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

import argparse
from config import SQLITE_PATH
from db import get_connection
from sources.semantic_scholar import SemanticScholarAdapter
from collect.multi_source_collector import upsert_paper


def collect_semantic_scholar(keyword: str, target: int = 10):
    """从 Semantic Scholar 搜索 keyword 并入库前 target 条结果。"""
    adapter = SemanticScholarAdapter()
    conn = get_connection(init_schema=False)
    inserted = 0
    try:
        page_size = min(target, 20)
        items = adapter.fetch(
            keyword, page=0, page_size=page_size, start_date=None, end_date=None
        )
        if not items:
            print("未获取到任何文献")
            return 0

        for item in items[:target]:
            paper_id = upsert_paper(conn, item, source="semantic_scholar")
            doi = item.get("DOI") or "(no DOI)"
            title = item.get("title") or "(no title)"
            if paper_id:
                inserted += 1
                print(f"[✓] 入库 paper_id={paper_id} | {doi} | {title[:60]}")
            else:
                print(f"[✗] 跳过 | {doi} | {title[:60]}")
        return inserted
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic Scholar 采集入库")
    parser.add_argument("--keyword", required=True, help="搜索关键词")
    parser.add_argument("--target", type=int, default=10, help="目标采集数量")
    args = parser.parse_args()

    count = collect_semantic_scholar(args.keyword, args.target)
    print(f"\n共入库 {count} 篇文献（目标 {args.target} 篇）")
