import psycopg2
from database import get_db_connection

def update_schema():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Checking schema...")
    
    # helper to add column if not exists
    def add_column(table, column, type_def):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_def}")
            conn.commit()
            print(f"Added column {column} to {table}")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print(f"Column {column} already exists in {table}")
        except Exception as e:
            conn.rollback()
            print(f"Error adding {column} to {table}: {e}")

    # USERS TABLE
    # Expected: id, email, name, avatar, status, lastSeen, synced
    add_column("users", "avatar", "TEXT")
    add_column("users", "status", "TEXT")
    add_column("users", "lastSeen", "TEXT")
    add_column("users", "synced", "BOOLEAN DEFAULT FALSE")

    # CHATS TABLE
    # Expected: id, name, type, participants, avatar, lastMessage, timestamp, isPrivate, createdBy, synced
    add_column("chats", "participants", "TEXT")
    add_column("chats", "avatar", "TEXT")
    add_column("chats", "lastMessage", "TEXT")
    add_column("chats", "timestamp", "TEXT")
    add_column("chats", "isPrivate", "BOOLEAN")
    add_column("chats", "createdBy", "TEXT")
    add_column("chats", "synced", "BOOLEAN DEFAULT FALSE")
    
    # MESSAGES TABLE
    # Expected: id... isPinned, callRoomName, callStatus, isVoice, replyTo, isDeleted, deleted_for, synced
    add_column("messages", "isPinned", "BOOLEAN DEFAULT FALSE")
    add_column("messages", "callRoomName", "TEXT")
    add_column("messages", "callStatus", "TEXT")
    add_column("messages", "isVoice", "BOOLEAN DEFAULT FALSE")
    add_column("messages", "replyTo", "TEXT")
    add_column("messages", "isDeleted", "BOOLEAN DEFAULT FALSE")
    add_column("messages", "deleted_for", "TEXT DEFAULT '[]'")
    add_column("messages", "synced", "BOOLEAN DEFAULT FALSE")
    
    # IDEAS TABLE
    add_column("ideas", "is_analyzed", "BOOLEAN DEFAULT FALSE")
    add_column("ideas", "synced", "BOOLEAN DEFAULT FALSE")

    conn.close()
    print("Schema check complete.")

if __name__ == "__main__":
    update_schema()
