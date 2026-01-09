
import sqlite3
import os

db_path = "/Users/dukekimm/Works/RAGaaS/backend/app/data/rag_system.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    # Try looking in the current directory if app/data path is relative or different
    db_path = "backend/app/data/rag_system.db"

if not os.path.exists(db_path):
    print("Database not found.")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, name, graph_backend FROM knowledge_bases")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} knowledge bases:")
    target_kb = None
    for row in rows:
        print(row)
        if row[1] == "test2":
            target_kb = row[0]

    if target_kb:
        print(f"FOUND test2 ID: {target_kb}")
    else:
        print("test2 NOT FOUND")
        
except Exception as e:
    print(f"Error querying database: {e}")

conn.close()
