import firebase_admin
from firebase_admin import credentials, firestore
import sqlite3
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Initialize Firebase
cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Initialize SQLite
from database import init_db, get_db_connection
init_db()
conn = get_db_connection()
cursor = conn.cursor()

def migrate_users():
    print("Migrating users...")
    users_ref = db.collection("users")
    for doc in users_ref.stream():
        user = doc.to_dict()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users (id, name, email, avatar, status, lastSeen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user.get("id"),
                user.get("name"),
                user.get("email"),
                user.get("avatar"),
                user.get("status"),
                user.get("lastSeen")
            ))
        except Exception as e:
            print(f"Error migrating user {user.get('id')}: {e}")
    conn.commit()

def migrate_chats():
    print("Migrating chats...")
    chats_ref = db.collection("chats")
    for doc in chats_ref.stream():
        chat = doc.to_dict()
        try:
            # Convert participants list to JSON string
            import json
            participants_json = json.dumps(chat.get("participants", []))
            
            cursor.execute('''
                INSERT OR REPLACE INTO chats (id, name, type, participants, avatar, lastMessage, timestamp, isPrivate, createdBy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat.get("id"),
                chat.get("name"),
                chat.get("type"),
                participants_json,
                chat.get("avatar"),
                chat.get("lastMessage"),
                chat.get("timestamp"),
                1 if chat.get("isPrivate") else 0,
                json.dumps(chat.get("createdBy")) if chat.get("createdBy") else None
            ))
            
            # Migrate messages for this chat
            migrate_messages(doc, chat.get("id"))
            
        except Exception as e:
            print(f"Error migrating chat {chat.get('id')}: {e}")
    conn.commit()

def migrate_messages(chat_doc, chat_id):
    print(f"  Migrating messages for chat {chat_id}...")
    messages_ref = chat_doc.reference.collection("messages")
    for msg_doc in messages_ref.stream():
        msg = msg_doc.to_dict()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO messages (id, chat_id, text, sender, time, type, fileUrl, fileName, fileSize, isPinned, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                msg.get("id"),
                chat_id,
                msg.get("text"),
                msg.get("sender"),
                msg.get("time"),
                msg.get("type", "text"),
                msg.get("fileUrl"),
                msg.get("fileName"),
                msg.get("fileSize"),
                1 if msg.get("isPinned") else 0
            ))
        except Exception as e:
            print(f"Error migrating message {msg.get('id')}: {e}")

def migrate_ideas():
    print("Migrating ideas...")
    ideas_ref = db.collection("ideas")
    for doc in ideas_ref.stream():
        idea = doc.to_dict()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO ideas (id, text, category, votes, timestamp, is_analyzed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                idea.get("id"),
                idea.get("text"),
                idea.get("category"),
                idea.get("votes", 0),
                idea.get("timestamp"),
                1 if idea.get("is_analyzed") else 0
            ))
        except Exception as e:
            print(f"Error migrating idea {idea.get('id')}: {e}")
    conn.commit()

if __name__ == "__main__":
    try:
        migrate_users()
        migrate_chats()
        migrate_ideas()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()
