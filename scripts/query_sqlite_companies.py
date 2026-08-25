import sqlite3
from collections import Counter

DB = 'db.sqlite3'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# list tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', [r[0] for r in cur.fetchall()])

for table in ['accounts_company','new__accounts_company']:
    try:
        cur.execute(f"SELECT id, name, domain FROM {table}")
        rows = cur.fetchall()
        print(f"\nTable: {table} - {len(rows)} rows")
        domains = [r[2] or '' for r in rows]
        counts = Counter(domains)
        print('duplicates:', {k:v for k,v in counts.items() if v>1})
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Table {table} not found or error: {e}")

conn.close()
