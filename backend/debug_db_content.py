import sqlite3
import json

DB_NAME = "backend/teamchat.db"

def inspect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Inspecting Messages Table ---")
    cursor.execute("SELECT id, text, isDeleted, deleted_for FROM messages ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"ID: {row['id']}")
        print(f"Text: {row['text']}")
        print(f"isDeleted: {row['isDeleted']}")
        print(f"deleted_for (Raw): {row['deleted_for']}")
        print(f"Type of deleted_for: {type(row['deleted_for'])}")
        
        try:
            parsed = json.loads(row['deleted_for'])
            print(f"Parsed JSON: {parsed}")
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            
        print("-" * 20)
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
