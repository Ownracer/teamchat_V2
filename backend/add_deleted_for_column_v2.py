import sqlite3
import json

DB_NAME = "backend/teamchat.db"

def migrate():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "deleted_for" not in columns:
            print("Adding deleted_for column...")
            cursor.execute("ALTER TABLE messages ADD COLUMN deleted_for TEXT DEFAULT '[]'")
            conn.commit()
            print("Migration successful: deleted_for column added.")
        else:
            print("Column deleted_for already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
