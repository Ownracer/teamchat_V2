import sqlite3
import json

def check_db():
    conn = sqlite3.connect('teamchat.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Checking Recent Messages ---")
    cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    
    for row in rows:
        msg = dict(row)
        print(f"ID: {msg['id']}, Type: {msg['type']}, FileName: {msg['fileName']}, FileSize: {msg['fileSize']}")
        
    conn.close()

if __name__ == "__main__":
    check_db()
