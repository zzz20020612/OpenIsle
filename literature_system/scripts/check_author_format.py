import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from db import get_connection

conn = get_connection(init_schema=False, row_factory=True)
cur = conn.cursor()
cur.execute("SELECT id, doi, author, source FROM papers WHERE author IS NOT NULL AND author != '' LIMIT 20")
for r in cur.fetchall():
    print(f"id={r['id']} source={r['source']} doi={r['doi']}")
    print(f"  author={r['author'][:200]}")
    try:
        parsed = json.loads(r['author'])
        print(f"  parsed type={type(parsed)}")
    except Exception as e:
        print(f"  not json: {e}")
    print()
conn.close()
