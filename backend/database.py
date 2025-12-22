import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# Default to local docker if not set
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:deb172006@localhost:5432/teamchat")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_db_cursor(conn):
    # Returns a cursor that yields dictionaries
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table
    # SQLite: INTEGER PRIMARY KEY -> PG: BIGSERIAL PRIMARY KEY (to support timestamp IDs)
    # SQLite: DEFAULT 0 -> PG: DEFAULT FALSE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT,
            avatar TEXT,
            status TEXT,
            lastSeen TEXT,
            synced BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Chats Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id BIGINT PRIMARY KEY,
            name TEXT,
            type TEXT,
            participants TEXT, -- JSON string
            avatar TEXT,
            lastMessage TEXT,
            timestamp TEXT,
            isPrivate BOOLEAN,
            createdBy TEXT, -- JSON string
            synced BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id BIGINT PRIMARY KEY, -- We use timestamp*1000, so BIGINT is safer
            chat_id BIGINT REFERENCES chats(id),
            text TEXT,
            sender TEXT,
            time TEXT,
            type TEXT,
            fileUrl TEXT,
            fileName TEXT,
            fileSize TEXT,
            isPinned BOOLEAN DEFAULT FALSE,
            callRoomName TEXT,
            callStatus TEXT,
            isVoice BOOLEAN DEFAULT FALSE,
            replyTo TEXT,
            isDeleted BOOLEAN DEFAULT FALSE,
            deleted_for TEXT DEFAULT '[]',
            synced BOOLEAN DEFAULT FALSE
        )
    ''')

    # Ideas Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id BIGINT PRIMARY KEY,
            text TEXT,
            category TEXT,
            votes INTEGER DEFAULT 0,
            timestamp TEXT,
            is_analyzed BOOLEAN DEFAULT FALSE,
            synced BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("PostgreSQL Database initialized.")

if __name__ == "__main__":
    init_db()
