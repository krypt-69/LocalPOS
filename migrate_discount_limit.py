import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'localpos.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(categories)")
columns = [col[1] for col in cursor.fetchall()]
if 'max_discount_percent' not in columns:
    cursor.execute("ALTER TABLE categories ADD COLUMN max_discount_percent REAL DEFAULT 0")
    print("Added max_discount_percent column to categories.")
else:
    print("Column already exists.")
conn.commit()
conn.close()
