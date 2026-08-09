"""
回填 papers.journal_tier 字段。
对所有 journal_tier IS NULL 的论文，根据 journal 名称重新计算分级并写入 DB。
分级规则来自 code/utils.py:get_journal_tier()，配置在 config/journal_tiers.json。

用法：python scripts/backfill_journal_tier.py
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from utils import get_journal_tier

DB = ROOT / "db" / "literature.db"

def main():
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    # 统计
    cur.execute("SELECT COUNT(*) FROM papers WHERE journal_tier IS NULL AND COALESCE(is_placeholder,0)=0")
    null_count = cur.fetchone()[0]
    print(f"待回填论文数: {null_count}")

    if null_count == 0:
        print("无需回填。")
        return

    # 取所有 NULL 的 (id, journal)
    cur.execute("""SELECT id, COALESCE(journal,'') FROM papers
                   WHERE journal_tier IS NULL AND COALESCE(is_placeholder,0)=0""")
    rows = cur.fetchall()
    print(f"实际扫描: {len(rows)} 行")

    # 预计算
    updates = []  # (tier, id)
    by_tier = {}
    no_journal = 0
    for pid, journal in rows:
        if not journal:
            no_journal += 1
            continue
        tier = get_journal_tier(journal)
        updates.append((tier, pid))
        by_tier[tier] = by_tier.get(tier, 0) + 1

    print(f"\n计算后分布:")
    for t in ("tier1", "tier2", "tier3", "other"):
        if t in by_tier:
            print(f"  {t:<8} {by_tier[t]:>3}")
    if no_journal:
        print(f"  <journal 为空>  {no_journal:>3} （保持 NULL）")

    # 批量更新
    cur.executemany("UPDATE papers SET journal_tier = ? WHERE id = ?", updates)
    conn.commit()
    print(f"\n已更新 {cur.rowcount} 行")

    # 验证
    cur.execute("""SELECT COALESCE(journal_tier,'<NULL>') AS t, COUNT(*) c
                   FROM papers WHERE COALESCE(is_placeholder,0)=0 GROUP BY t ORDER BY c DESC""")
    print("\n=== 回填后分布 ===")
    for r in cur.fetchall():
        print(f"  {r[0]:<8} {r[1]:>3}")

    conn.close()

if __name__ == "__main__":
    main()
