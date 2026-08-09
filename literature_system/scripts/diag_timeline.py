import sqlite3
from collections import defaultdict

DB = r"d:\Seadrive\吴相民 6020\我的资料库\Research\文献系统\db\literature.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

cur = conn.cursor()

# 1) 2024 年对比
print("=== 1) 2024 年对比 ===")
for label, sql in [
    ("论文数 (papers WHERE year=2024)",
     "SELECT COUNT(*) c FROM papers WHERE substr(published_date,1,4)='2024' AND published_date IS NOT NULL"),
    ("parse_jobs done 任务数 (按论文年份=2024)",
     "SELECT COUNT(*) c FROM parse_jobs j JOIN papers p ON p.id=j.paper_id WHERE j.status='done' AND substr(p.published_date,1,4)='2024'"),
    ("distinct 论文数 (去重 parse_jobs done)",
     "SELECT COUNT(DISTINCT j.paper_id) c FROM parse_jobs j JOIN papers p ON p.id=j.paper_id WHERE j.status='done' AND substr(p.published_date,1,4)='2024'"),
    ("parse_jobs 全状态 (按论文年份=2024)",
     "SELECT COUNT(*) c FROM parse_jobs j JOIN papers p ON p.id=j.paper_id WHERE substr(p.published_date,1,4)='2024'"),
]:
    cur.execute(sql)
    print(f"  {label}: {cur.fetchone()['c']}")

# 2) 2024 论文列表 vs 哪些有 done 任务
print("\n=== 2) 2024 所有论文 vs done 状态论文 ===")
cur.execute("SELECT id, doi, title FROM papers WHERE substr(published_date,1,4)='2024' AND published_date IS NOT NULL")
all_2024 = cur.fetchall()
cur.execute("SELECT DISTINCT j.paper_id FROM parse_jobs j JOIN papers p ON p.id=j.paper_id WHERE j.status='done' AND substr(p.published_date,1,4)='2024'")
done_2024 = {r['paper_id'] for r in cur.fetchall()}
print(f"  2024 论文总数: {len(all_2024)}")
print(f"  2024 至少一条 done 的论文数: {len(done_2024)}")
print(f"  2024 没有 done 的论文数: {len(all_2024) - len(done_2024)}")

# 3) parse_jobs 按论文看分布
print("\n=== 3) 同一篇论文的多条 done 任务（2024）===")
cur.execute("""
    SELECT j.paper_id, COUNT(*) c
    FROM parse_jobs j JOIN papers p ON p.id=j.paper_id
    WHERE j.status='done' AND substr(p.published_date,1,4)='2024'
    GROUP BY j.paper_id HAVING COUNT(*) > 1 ORDER BY c DESC LIMIT 10
""")
for r in cur.fetchall():
    print(f"  paper_id={r['paper_id']}, done jobs={r['c']}")

# 4) parse_jobs 状态分布
print("\n=== 4) parse_jobs 状态分布 (按论文年份) ===")
cur.execute("""
    SELECT substr(p.published_date,1,4) yr, j.status, COUNT(*) c
    FROM parse_jobs j JOIN papers p ON p.id=j.paper_id
    WHERE p.published_date IS NOT NULL AND substr(p.published_date,1,4) GLOB '[0-9]*'
    GROUP BY yr, status ORDER BY yr, status
""")
for r in cur.fetchall():
    print(f"  {r['yr']}  {r['status']:<18} {r['c']}")

# 5) parse_jobs 跨年 vs papers 跨年
print("\n=== 5) 完整对比 (paper / parse_done_jobs / distinct_done_papers) ===")
cur.execute("SELECT substr(published_date,1,4) y, COUNT(*) c FROM papers WHERE published_date IS NOT NULL AND substr(published_date,1,4) GLOB '[0-9]*' GROUP BY y")
papers = {r['y']: r['c'] for r in cur.fetchall()}
cur.execute("SELECT substr(p.published_date,1,4) y, COUNT(*) c FROM parse_jobs j JOIN papers p ON p.id=j.paper_id WHERE j.status='done' AND p.published_date IS NOT NULL AND substr(p.published_date,1,4) GLOB '[0-9]*' GROUP BY y")
jobs = {r['y']: r['c'] for r in cur.fetchall()}
cur.execute("SELECT substr(p.published_date,1,4) y, COUNT(DISTINCT j.paper_id) c FROM parse_jobs j JOIN papers p ON p.id=j.paper_id WHERE j.status='done' AND p.published_date IS NOT NULL AND substr(p.published_date,1,4) GLOB '[0-9]*' GROUP BY y")
distinct = {r['y']: r['c'] for r in cur.fetchall()}
all_y = sorted(set(papers) | set(jobs) | set(distinct))
print(f"  {'year':<6}{'papers':>8}{'parse_done_jobs':>18}{'distinct_done_papers':>22}{'jobs-papers':>14}")
for y in all_y:
    p, j, d = papers.get(y,0), jobs.get(y,0), distinct.get(y,0)
    print(f"  {y:<6}{p:>8}{j:>18}{d:>22}{j-p:>+14}")

conn.close()
