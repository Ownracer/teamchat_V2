import sqlite3

def add_members_column():
    conn = sqlite3.connect('teamchat.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE chats ADD COLUMN members INTEGER DEFAULT 1")
        print("Column 'members' added successfully.")
        
        # Backfill
        import json
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor() # helper cursor
        cursor.execute("SELECT id, participants FROM chats")
        chats = cursor.fetchall()
        for chat in chats:
            try:
                parts = json.loads(chat['participants'])
                count = len(parts)
                cursor.execute("UPDATE chats SET members = ? WHERE id = ?", (count, chat['id']))
                print(f"Updated Chat {chat['id']} with {count} members.")
            except:
                pass
    except Exception as e:
        print(f"Error adding column (might exist): {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_members_column()
