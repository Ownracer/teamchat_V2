import json
import time
from database import get_db_connection, get_db_cursor
from datetime import datetime

def test_create_call():
    print("--- Testing Call Creation Logic ---")
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    chat_id = int(time.time() * 1000)
    msg_id = chat_id + 5
    user_id = chat_id + 1
    room_name = f"TestRoom-{chat_id}"
    
    try:
        # Create Chat & User
        cursor.execute("INSERT INTO users (id, name, email) VALUES (%s, 'Test', 't@t.com') ON CONFLICT DO NOTHING", (user_id,))
        cursor.execute("INSERT INTO chats (id, name, type, participants) VALUES (%s, 'Call Test', 'private', '[]')", (chat_id,))
        
        # Insert Call Message
        print(f"Inserting Call Message with room: {room_name}")
        cursor.execute("""
            INSERT INTO messages (id, chat_id, text, sender, time, type, callStatus, callRoomName) 
            VALUES (%s, %s, 'Call Start', %s, '12:00', 'call', 'active', %s)
        """, (msg_id, chat_id, str(user_id), room_name))
        conn.commit()
        
        # Verify Retrieval
        cursor.execute("SELECT callRoomName, type, callStatus FROM messages WHERE id = %s", (msg_id,))
        row = cursor.fetchone()
        
        print(f"Retrieved Row: {dict(row)}")
        
        if row['callroomname'] == room_name:
            print("SUCCESS: callRoomName persisted correctly.")
        else:
            print(f"FAILURE: callRoomName mismatch. Expected {room_name}, got {row['callroomname']}")
            
    except Exception as e:
        print(f"Error: {e}")
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
    test_create_call()
