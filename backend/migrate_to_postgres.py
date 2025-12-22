import sqlite3
import psycopg2
from database import get_db_connection, init_db
import os

# Source
SQLITE_DB = "teamchat.db"

def migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"No SQLite database found at {SQLITE_DB}. Skipping migration.")
        return

    print("Initializing PostgreSQL Schema...")
    init_db()
    
    # Connections
    pg_conn = get_db_connection()
    pg_cursor = pg_conn.cursor()
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    try:
        # 1. Users
        print("Migrating Users...")
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        for user in users:
            pg_cursor.execute("""
                INSERT INTO users (id, email, name, avatar, status, lastSeen, synced)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (user['id'], user['email'], user['name'], user['avatar'], user['status'], user['lastSeen'], bool(user['synced'])))
            
        # 2. Chats
        print("Migrating Chats...")
        sqlite_cursor.execute("SELECT * FROM chats")
        chats = sqlite_cursor.fetchall()
        for chat in chats:
            pg_cursor.execute("""
                INSERT INTO chats (id, name, type, participants, avatar, lastMessage, timestamp, isPrivate, createdBy, synced)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                chat['id'], chat['name'], chat['type'], chat['participants'], chat['avatar'], 
                chat['lastMessage'], chat['timestamp'], bool(chat['isPrivate']), chat['createdBy'], bool(chat['synced'])
            ))
            
        # 3. Messages
        print("Migrating Messages...")
        sqlite_cursor.execute("SELECT * FROM messages")
        messages = sqlite_cursor.fetchall()
        for msg in messages:
            pg_cursor.execute("""
                INSERT INTO messages (
                    id, chat_id, text, sender, time, type, fileUrl, fileName, fileSize, 
                    isPinned, callRoomName, callStatus, isVoice, replyTo, isDeleted, deleted_for, synced
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                msg['id'], msg['chat_id'], msg['text'], msg['sender'], msg['time'], msg['type'], 
                msg['fileUrl'], msg['fileName'], msg['fileSize'], 
                bool(msg['isPinned']), msg['callRoomName'], msg['callStatus'], bool(msg['isVoice']), 
                msg['replyTo'], bool(msg['isDeleted']), msg['deleted_for'], bool(msg['synced'])
            ))

        # 4. Ideas
        print("Migrating Ideas...")
        sqlite_cursor.execute("SELECT * FROM ideas")
        ideas = sqlite_cursor.fetchall()
        for idea in ideas:
            pg_cursor.execute("""
                INSERT INTO ideas (id, text, category, votes, timestamp, is_analyzed, synced)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                idea['id'], idea['text'], idea['category'], idea['votes'], idea['timestamp'], 
                bool(idea['is_analyzed']), bool(idea['synced'])
            ))
            
        pg_conn.commit()
        print("Migration Complete Successfully.")
        
    except Exception as e:
        print(f"Migration Failed: {e}")
        pg_conn.rollback()
    finally:
        pg_conn.close()
        sqlite_conn.close()

if __name__ == "__main__":
    migrate()
