#!/usr/bin/env python3
"""
修复 parse_jobs 与 paper_sections 数据不一致问题。

场景：某些论文已有 paper_sections 数据，但 parse_jobs 表中缺少 done 记录。
这会导致 process_paper 的跳过逻辑失效，重复执行 PDF 解析。

本脚本会为这些论文补录一条 status='done' 的 parse_jobs 记录，
parser_used 标记为 'manual_fix'，便于追溯。
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "literature.db"


def fix():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 找出已有 section 但缺少 done 记录的论文
    cur.execute("""
        SELECT DISTINCT p.id, p.doi, p.title
        FROM papers p
        WHERE EXISTS (SELECT 1 FROM paper_sections ps WHERE ps.paper_id = p.id)
        AND NOT EXISTS (SELECT 1 FROM parse_jobs pj WHERE pj.paper_id = p.id AND pj.status = 'done')
    """)
    rows = cur.fetchall()

    if not rows:
        print("无需修复：所有有 section 的论文都有 parse_jobs done 记录。")
        conn.close()
        return

    print(f"发现 {len(rows)} 篇论文需要修复：")
    for paper_id, doi, title in rows:
        print(f"  - ID {paper_id}: {title or doi}")

    cur.executemany(
        """
        INSERT INTO parse_jobs (paper_id, stage, status, parser_used, error_msg, finished_at)
        VALUES (?, 'parse', 'done', 'manual_fix', 'Auto-fixed: paper_sections exists but no done job', datetime('now'))
        """,
        [(paper_id,) for paper_id, _, _ in rows]
    )
    conn.commit()
    print(f"已插入 {cur.rowcount} 条 parse_jobs done 记录。")
    conn.close()


if __name__ == "__main__":
    fix()
