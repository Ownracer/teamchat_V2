import asyncio
import json
import psycopg2
from database import get_db_connection, get_db_cursor
import time

def test_end_call_logic():
    print("--- Testing End Call Logic (DB Update) ---")
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    # 1. Setup: Create Dummy User, Chat, Message
    chat_id = int(time.time() * 1000)
    user_id = chat_id + 1
    msg_id = chat_id + 2
    
    print(f"Creating Test Chat: {chat_id}, Msg: {msg_id}")
    
    try:
        # User
        cursor.execute("INSERT INTO users (id, name, email) VALUES (%s, 'Test User', 'test@example.com') ON CONFLICT DO NOTHING", (user_id,))
        
        # Chat
        participants = [{"id": user_id, "name": "Test User"}]
        cursor.execute("INSERT INTO chats (id, name, type, participants) VALUES (%s, 'Test Chat', 'private', %s)", (chat_id, json.dumps(participants)))
        
        # Message (Start Call)
        cursor.execute("""
            INSERT INTO messages (id, chat_id, text, sender, time, type, callStatus, callRoomName) 
            VALUES (%s, %s, 'Call Started', %s, '12:00', 'call', 'active', 'room-123')
        """, (msg_id, chat_id, str(user_id)))
        conn.commit()
        print("Initial Call Message Created.")
        
        # 2. Simulate Update (End Call)
        updates = {"callStatus": "ended", "text": "Call Ended"}
        
        # Logic copied from update_message in main.py
        fields = []
        values = []
        for k, v in updates.items():
            fields.append(f"{k} = %s")
            values.append(v)
            
        values.append(msg_id)
        
        sql = f"UPDATE messages SET {', '.join(fields)} WHERE id = %s"
        print(f"Executing SQL: {sql}")
        print(f"Values: {values}")
        
        cursor.execute(sql, values)
        conn.commit()
        
        # 3. Verify
        cursor.execute("SELECT callStatus, text FROM messages WHERE id = %s", (msg_id,))
        row = cursor.fetchone()
        print(f"Updated Row: {dict(row)}")
        
        if row['callstatus'] == 'ended': # Note: psycopg2 RealDictCursor usually indicates casing, but Postgres is case-insensitive for columns? No, keys are lower case usually.
            print("SUCCESS: callStatus updated to 'ended'")
        else:
            print("FAILURE: callStatus not updated")
            
    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        # Cleanup
        try:
            cursor.execute("DELETE FROM messages WHERE id = %s", (msg_id,))
            cursor.execute("DELETE FROM chats WHERE id = %s", (chat_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        except:
            pass
        conn.close()

if __name__ == "__main__":
    test_end_call_logic()
