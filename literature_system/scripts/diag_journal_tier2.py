import sqlite3
DB = r"d:\Seadrive\吴相民 6020\我的资料库\Research\文献系统\db\literature.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 所有应该有分级的论文 → 看实际 journal_tier
print("=== 应被分级却仍为 NULL 的论文 ===")
cur.execute("""
    SELECT id, journal, journal_tier
    FROM papers
    WHERE COALESCE(is_placeholder,0)=0
      AND (LOWER(journal) IN ('nature','science','cell','the lancet','lancet','pnas',
                              'nature communications','nature sustainability','nature climate change',
                              'nature geoscience','nature food','nature cities','nature energy','nature water',
                              'nature methods','nature medicine','nature biotechnology','nature chemistry',
                              'nature physics','nature materials','nature ecology & evolution',
                              'nature human behaviour','nature plants','nature microbiology','nature catalysis',
                              'the lancet planetary health','nature reviews earth & environment',
                              'nature reviews microbiology','nature reviews bioengineering',
                              'proceedings of the national academy of sciences of the united states of america',
                              'science advances','science bulletin')
           OR LOWER(journal) IN ('environmental science & technology','environmental science and technology',
                                 'water research','global environmental change','journal of cleaner production',
                                 'resources conservation and recycling','resources, conservation and recycling',
                                 'waste management','bioresource technology',
                                 'acs sustainable chemistry & engineering','chemical engineering journal',
                                 'science of the total environment','science of the total environment',
                                 'journal of hazardous materials','environment international'))
    ORDER BY journal
""")
hits = cur.fetchall()
print(f"命中 {len(hits)} 篇")
for r in hits:
    print(f"  id={r[0]:<4} tier={str(r[2]):<8} journal={r[1]}")

# 也看 Tier1/2/3 各类被赋值数
print("\n=== 真实 tier 分布（除 NULL）===")
cur.execute("""SELECT COALESCE(journal_tier,'<NULL>') AS t, COUNT(*) c
FROM papers WHERE COALESCE(is_placeholder,0)=0 GROUP BY t ORDER BY c DESC""")
for r in cur.fetchall():
    print(f"  {r[0]:<10} {r[1]}")

# 全部 49 篇中实际 journal 不为 NULL 的
print("\n=== 所有 paper 的 journal 和 tier（去重 journal）===")
cur.execute("""SELECT COALESCE(journal,'<NULL>') j, COALESCE(journal_tier,'<NULL>') t, COUNT(*) c
FROM papers WHERE COALESCE(is_placeholder,0)=0 GROUP BY j, t ORDER BY c DESC""")
for r in cur.fetchall():
    print(f"  {r[0][:55]:<55} {r[1]:<8} x{r[2]}")

conn.close()
