import sqlite3
import json

def check_participants():
    try:
        conn = sqlite3.connect('teamchat.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, participants FROM chats")
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} chats.")
        for row in rows:
            print("-" * 30)
            print(f"Chat ID: {row['id']}")
            print(f"Name: {row['name']}")
            
            try:
                parts = json.loads(row['participants'])
                print(f"Participants JSON ({len(parts)}):")
                for p in parts:
                    print(f" - {p.get('name')} (ID: {p.get('id')})")
            except Exception as e:
                print(f"Error parsing participants JSON: {e}")
                print(f"Raw: {row['participants']}")
                
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    check_participants()
