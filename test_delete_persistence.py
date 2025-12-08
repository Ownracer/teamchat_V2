import requests
import sqlite3
import json
import time

API_URL = "http://localhost:8000"
DB_NAME = "backend/teamchat.db"

def test_persistence():
    # 1. Insert Dummy Message directly to DB
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    test_msg_id = int(time.time() * 1000)
    chat_id = 1
    user_id = 999
    
    print(f"Test Msg ID: {test_msg_id}")
    
    cursor.execute('''
        INSERT INTO messages (id, chat_id, text, sender, time, type, deleted_for, synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (test_msg_id, chat_id, "Test Persistence Message", str(user_id), "12:00", "text", "[]", 0))
    conn.commit()
    conn.close()
    
    # 2. Call Delete Endoint
    url = f"{API_URL}/chats/{chat_id}/messages/{test_msg_id}/delete_for_me"
    payload = {"user_id": user_id}
    print(f"Calling DELETE endpoint: {url} with {payload}")
    
    try:
        res = requests.post(url, json=payload)
        print(f"Response Status: {res.status_code}")
        print(f"Response Body: {res.text}")
    except Exception as e:
        print(f"Request Failed: {e}")
        return

    # 3. Check DB Update
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT deleted_for FROM messages WHERE id = ?", (test_msg_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"DB deleted_for value: {row[0]}")
        if str(user_id) in row[0]:
            print("SUCCESS: User ID found in DB.")
        else:
            print("FAILURE: User ID NOT found in DB.")
    else:
        print("FAILURE: Message not found in DB.")

    # 4. Check Get Messages Filter
    get_url = f"{API_URL}/chats/{chat_id}/messages?user_id={user_id}"
    print(f"Calling GET messages: {get_url}")
    res = requests.get(get_url)
    messages = res.json()
    
    found = any(m['id'] == test_msg_id for m in messages)
    if found:
        print("FAILURE: Message still returned in GET list.")
        failed_msg = next(m for m in messages if m['id'] == test_msg_id)
        print(f"Returned Message: {failed_msg}")
    else:
        print("SUCCESS: Message filtered out from GET list.")

if __name__ == "__main__":
    test_persistence()
