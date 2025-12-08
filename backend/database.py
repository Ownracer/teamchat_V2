import sqlite3
import json
from datetime import datetime

DB_NAME = "teamchat.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT,
            avatar TEXT,
            status TEXT,
            lastSeen TEXT,
            synced BOOLEAN DEFAULT 0
        )
    ''')
    
    # Chats Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            participants TEXT, -- JSON string
            avatar TEXT,
            lastMessage TEXT,
            timestamp TEXT,
            isPrivate BOOLEAN,
            createdBy TEXT, -- JSON string
            synced BOOLEAN DEFAULT 0
        )
    ''')
    
    # Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            text TEXT,
            sender TEXT,
            time TEXT,
            type TEXT,
            fileUrl TEXT,
            fileName TEXT,
            fileSize TEXT,
            isPinned BOOLEAN DEFAULT 0,
            callRoomName TEXT,
            callStatus TEXT,
            isVoice BOOLEAN DEFAULT 0,
            replyTo TEXT,
            isDeleted BOOLEAN DEFAULT 0,
            deleted_for TEXT DEFAULT '[]',
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (chat_id) REFERENCES chats (id)
        )
    ''')

    # Ideas Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY,
            text TEXT,
            category TEXT,
            votes INTEGER DEFAULT 0,
            timestamp TEXT,
            is_analyzed BOOLEAN DEFAULT 0,
            synced BOOLEAN DEFAULT 0
        )
    ''')

    
    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
