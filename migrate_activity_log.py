import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'localpos.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        target_type TEXT,
        target_id INTEGER,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_log(action)")
conn.commit()
conn.close()
print("✅ Activity log table created.")
