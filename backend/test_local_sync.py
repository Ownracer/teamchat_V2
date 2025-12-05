import requests
import sqlite3
import time
import json

BASE_URL = "http://127.0.0.1:8000"
DB_NAME = "backend/teamchat.db"
CHAT_ID = 1 # Assuming chat 1 exists

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def test_sync():
    # 1. Send Message
    print("Sending message...")
    msg = {
        "text": "Local Sync Test Message",
        "sender": "test_sync",
        "time": "12:00 PM"
    }
    res = requests.post(f"{BASE_URL}/chats/{CHAT_ID}/messages", json=msg)
    if res.status_code != 200:
        print(f"Failed to send message: {res.text}")
        return
    
    msg_data = res.json()
    msg_id = msg_data["id"]
    print(f"Message sent with ID: {msg_id}")
    
    # 2. Verify in SQLite
    print("Verifying in SQLite...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    
    if row:
        print("Success: Message found in SQLite.")
        print(f"Synced status: {row['synced']}")
    else:
        print("Failure: Message NOT found in SQLite.")
        conn.close()
        return

    conn.close()
    
    # 3. Wait for Sync (Background Task)
    print("Waiting for sync...")
    time.sleep(5)
    
    # 4. Verify Synced Status in SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    
    if row and row['synced'] == 1:
        print("Success: Message marked as synced in SQLite.")
    else:
        print(f"Failure: Message synced status is {row['synced'] if row else 'None'}.")
        
    conn.close()

if __name__ == "__main__":
    test_sync()
