import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from db import get_connection

conn = get_connection(init_schema=False, row_factory=True)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) AS c FROM papers"); print("papers:", cur.fetchone()["c"])
cur.execute("SELECT COUNT(*) AS c FROM paper_fulltext"); print("parsed:", cur.fetchone()["c"])
cur.execute("SELECT COUNT(*) AS c FROM paper_knowledge_cards"); print("knowledge cards:", cur.fetchone()["c"])
cur.execute("SELECT COUNT(*) AS c FROM paper_methods"); print("methods:", cur.fetchone()["c"])
cur.execute("SELECT COUNT(*) AS c FROM paper_data_points"); print("data points:", cur.fetchone()["c"])
cur.execute("SELECT COUNT(*) AS c FROM paper_embeddings"); print("embeddings:", cur.fetchone()["c"])
cur.execute("SELECT source, COUNT(*) AS c FROM papers WHERE id >= 82 GROUP BY source")
print("new papers by source:", [dict(r) for r in cur.fetchall()])
conn.close()
