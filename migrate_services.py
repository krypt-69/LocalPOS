#!/usr/bin/env python3
"""One‑time migration to add service tables and link debtors."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'localpos.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add source and source_id to debtors (if not exists)
    cursor.execute("PRAGMA table_info(debtors)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'source' not in columns:
        cursor.execute("ALTER TABLE debtors ADD COLUMN source TEXT DEFAULT 'sale'")
    if 'source_id' not in columns:
        cursor.execute("ALTER TABLE debtors ADD COLUMN source_id INTEGER")

    # 2. Create service_categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Create service_types (belongs to category, has max_charge)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            max_charge REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES service_categories(id) ON DELETE CASCADE
        )
    """)

    # 4. Create service_jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            service_type_id INTEGER NOT NULL,
            service_category_id INTEGER NOT NULL,
            item_description TEXT NOT NULL,
            issue_description TEXT,
            status TEXT DEFAULT 'received',
            expected_completion_date DATE,
            service_charge REAL DEFAULT 0,
            parts_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            amount_paid REAL DEFAULT 0,
            balance REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'unpaid',
            notes TEXT,
            technician_notes TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            collected_at TIMESTAMP,
            FOREIGN KEY (service_type_id) REFERENCES service_types(id),
            FOREIGN KEY (service_category_id) REFERENCES service_categories(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    # 5. Create service_history (timeline)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            status_from TEXT,
            status_to TEXT,
            notes TEXT,
            changed_by INTEGER NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES service_jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (changed_by) REFERENCES users(id)
        )
    """)

    # 6. Insert default service categories
    default_categories = ['Repair', 'Installation', 'Maintenance', 'Contract', 'Training', 'Other']
    for cat in default_categories:
        cursor.execute("INSERT OR IGNORE INTO service_categories (name) VALUES (?)", (cat,))

    # 7. Insert example service types (owner will edit later)
    cursor.execute("SELECT id FROM service_categories WHERE name = 'Repair'")
    repair_cat = cursor.fetchone()
    if repair_cat:
        examples = [
            ('Laptop Repair', 10000),
            ('Printer Repair', 8000),
            ('Phone Repair', 5000),
        ]
        for name, max_charge in examples:
            cursor.execute("INSERT OR IGNORE INTO service_types (category_id, name, max_charge) VALUES (?, ?, ?)",
                           (repair_cat[0], name, max_charge))

    conn.commit()
    conn.close()
    print("✅ Services migration complete.")
    print("   - Added source/source_id to debtors")
    print("   - Created service_categories, service_types, service_jobs, service_history")
    print("   - Inserted default categories and example service types")

if __name__ == '__main__':
    migrate()
