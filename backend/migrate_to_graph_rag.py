"""
Database migration to add Graph RAG support

This migration:
1. Removes the metric_type column (all KBs will use COSINE by default)
2. Adds enable_graph_rag column (boolean, default False)
3. Adds graph_config column (JSON, nullable)
"""

import sqlite3
import os
import json

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'rag_system.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping migration")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if migration has already been applied
        cursor.execute("PRAGMA table_info(knowledge_bases)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'enable_graph_rag' in columns:
            print("Migration already applied, skipping...")
            conn.close()
            return
        
        print("Starting migration...")
        
        # Create new table with updated schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases_new (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                chunking_strategy TEXT DEFAULT 'size',
                chunking_config TEXT DEFAULT '{}',
                enable_graph_rag INTEGER DEFAULT 0,
                graph_config TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Copy data from old table (excluding metric_type)
        cursor.execute("""
            INSERT INTO knowledge_bases_new 
            (id, name, description, chunking_strategy, chunking_config, created_at, updated_at)
            SELECT id, name, description, chunking_strategy, chunking_config, created_at, updated_at
            FROM knowledge_bases
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE knowledge_bases")
        
        # Rename new table
        cursor.execute("ALTER TABLE knowledge_bases_new RENAME TO knowledge_bases")
        
        # Create index
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_bases_name ON knowledge_bases (name)")
        
        conn.commit()
        print("Migration completed successfully!")
        print("- Removed metric_type column")
        print("- Added enable_graph_rag column")
        print("- Added graph_config column")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
