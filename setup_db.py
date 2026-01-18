import sqlite3

conn = sqlite3.connect("requisitions.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS requisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    type TEXT,
    department TEXT,
    requestor TEXT,
    purpose TEXT,
    amount REAL,
    status TEXT,
    approved_by TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_id INTEGER,
    action TEXT,
    performed_by TEXT,
    role TEXT,
    timestamp TEXT
)
""")

conn.commit()
conn.close()

print("Database setup completed successfully.")