import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from db import get_connection

conn = get_connection(init_schema=False, row_factory=True)
cur = conn.cursor()

tables = ["authors", "paper_authors", "paper_affiliations", "affiliations"]
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) AS c FROM {t}")
        print(f"{t}: {cur.fetchone()['c']} rows")
    except Exception as e:
        print(f"{t}: {e}")

# sample authors
try:
    cur.execute("SELECT * FROM authors LIMIT 3")
    print("\nSample authors:")
    for r in cur.fetchall():
        print(dict(r))
except Exception as e:
    print("authors sample error:", e)

conn.close()
