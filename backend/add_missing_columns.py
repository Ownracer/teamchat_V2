
import sqlite3

DB_NAME = "backend/teamchat.db"

def migrate():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Check for 'isDeleted'
    cursor.execute("PRAGMA table_info(messages)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "isDeleted" not in columns:
        print("Adding 'isDeleted' column...")
        cursor.execute("ALTER TABLE messages ADD COLUMN isDeleted BOOLEAN DEFAULT 0")
    else:
        print("'isDeleted' already exists.")
        
    if "replyTo" not in columns:
        print("Adding 'replyTo' column...")
        cursor.execute("ALTER TABLE messages ADD COLUMN replyTo TEXT")
    else:
        print("'replyTo' already exists.")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
