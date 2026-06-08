#!/usr/bin/env python3
"""One-time migration to add role and last_login columns to User table."""
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'localpos.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if role column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'role' not in columns:
        print("Adding 'role' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'worker'")
    
    if 'last_login' not in columns:
        print("Adding 'last_login' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    
    # Set initial roles for user1 and user2
    cursor.execute("UPDATE users SET role = 'owner' WHERE username = 'user1'")
    cursor.execute("UPDATE users SET role = 'worker' WHERE username = 'user2'")
    
    # Ensure both are active
    cursor.execute("UPDATE users SET is_active = 1 WHERE username IN ('user1', 'user2')")
    
    conn.commit()
    conn.close()
    print("Migration complete. user1 = owner, user2 = worker.")

if __name__ == '__main__':
    migrate()
