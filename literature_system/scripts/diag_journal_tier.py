import sqlite3
DB = r"d:\Seadrive\吴相民 6020\我的资料库\Research\文献系统\db\literature.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== 1) journal_tier 字段填充情况 ===")
cur.execute("SELECT COALESCE(journal_tier,'<NULL>') AS tier, COUNT(*) AS c FROM papers WHERE COALESCE(is_placeholder,0)=0 GROUP BY tier ORDER BY c DESC")
for r in cur.fetchall():
    print(f"  {r[0]:<10} {r[1]}")

print("\n=== 2) journal_tier 是 NULL 的论文，按 journal 名称分组 ===")
cur.execute("SELECT journal, COUNT(*) c FROM papers WHERE journal_tier IS NULL AND COALESCE(is_placeholder,0)=0 GROUP BY journal ORDER BY c DESC LIMIT 20")
for r in cur.fetchall():
    print(f"  {r[0] or '<NULL>':<60} {r[1]}")

print("\n=== 3) 已分类的论文示例 ===")
cur.execute("SELECT id, journal, journal_tier FROM papers WHERE journal_tier IS NOT NULL AND COALESCE(is_placeholder,0)=0 ORDER BY journal_tier, id LIMIT 20")
for r in cur.fetchall():
    print(f"  id={r[0]:<4} tier={r[2]:<8} journal={r[1]}")

print("\n=== 4) 按 tier+year 统计 ===")
cur.execute("""SELECT
  COALESCE(journal_tier,'<NULL>') AS tier,
  substr(published_date,1,4) AS y,
  COUNT(*) c
FROM papers WHERE COALESCE(is_placeholder,0)=0
GROUP BY tier, y ORDER BY tier, y""")
for r in cur.fetchall():
    print(f"  {r[0]:<10} {r[1]:<6} {r[2]}")

print("\n=== 5) 来源 source 分布 ===")
cur.execute("SELECT COALESCE(source,'<NULL>') s, COUNT(*) c FROM papers WHERE COALESCE(is_placeholder,0)=0 GROUP BY s ORDER BY c DESC")
for r in cur.fetchall():
    print(f"  {r[0]:<30} {r[1]}")

conn.close()
