import sqlite3
import os

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DROP VIEW IF EXISTS enrollments_salesrecord")
        conn.commit()
        print("Dropped view successfully")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("DB file not found")
