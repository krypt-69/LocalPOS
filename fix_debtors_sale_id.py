import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'localpos.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if sale_id has NOT NULL constraint
cursor.execute("PRAGMA table_info(debtors)")
columns = cursor.fetchall()
sale_id_col = None
for col in columns:
    if col[1] == 'sale_id':
        sale_id_col = col
        break

if sale_id_col and sale_id_col[3] == 1:  # notnull flag is 1 (True)
    print("Removing NOT NULL constraint from sale_id...")
    # SQLite workaround: create new table without NOT NULL, copy data, swap
    cursor.execute("""
        CREATE TABLE debtors_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            source TEXT DEFAULT 'sale',
            source_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            total_owed REAL NOT NULL,
            amount_paid REAL DEFAULT 0,
            balance REAL NOT NULL,
            due_date DATE,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Copy data
    cursor.execute("""
        INSERT INTO debtors_new (
            id, sale_id, source, source_id, customer_name, customer_phone,
            total_owed, amount_paid, balance, due_date, status, notes, created_at, updated_at
        )
        SELECT 
            id, sale_id, source, source_id, customer_name, customer_phone,
            total_owed, amount_paid, balance, due_date, status, notes, created_at, updated_at
        FROM debtors
    """)
    cursor.execute("DROP TABLE debtors")
    cursor.execute("ALTER TABLE debtors_new RENAME TO debtors")
    # Recreate indexes
    cursor.execute("CREATE INDEX idx_debtors_sale_id ON debtors(sale_id)")
    cursor.execute("CREATE INDEX idx_debtors_source ON debtors(source, source_id)")
    conn.commit()
    print("✅ Fixed: sale_id can now be NULL.")
else:
    print("sale_id already allows NULL or not found.")

conn.close()
