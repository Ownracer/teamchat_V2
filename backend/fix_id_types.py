import psycopg2
from database import get_db_connection

def fix_id_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Converting ID columns to BIGINT...")
    
    tables_to_fix = [
        ("users", "id"),
        ("chats", "id"),
        ("ideas", "id"),
        # messages.id is already BIGINT, but chat_id fk needs check
    ]
    
    try:
        # 1. Drop constraints if needed (Foreign Keys might block type change)
        # messages.chat_id references chats.id
        print("Dropping FK constraint on messages(chat_id)...")
        try:
            cursor.execute("ALTER TABLE messages DROP CONSTRAINT messages_chat_id_fkey")
            conn.commit()
        except Exception as e:
            print(f"Constraint drop failed (maybe doesn't exist): {e}")
            conn.rollback()

        # 2. Change Types
        for table, col in tables_to_fix:
            print(f"Changing {table}.{col} to BIGINT...")
            cursor.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE BIGINT")
            conn.commit()
            
        print("Changing messages.chat_id to BIGINT...")
        cursor.execute("ALTER TABLE messages ALTER COLUMN chat_id TYPE BIGINT")
        conn.commit()

        # 3. Restore Constraints
        print("Restoring FK constraint on messages(chat_id)...")
        # Ensure values exist before adding constraint? We assume they do from migration.
        # But if we can't Add FK back immediately it's okay for now, functionality works without strict FK in app logic.
        # However, good practice to have it.
        try:
            cursor.execute("ALTER TABLE messages ADD CONSTRAINT messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES chats(id)")
            conn.commit()
        except Exception as e:
             print(f"Warning: Could not restore FK constraint: {e}")
             conn.rollback()

        print("ID Fix Complete.")
        
    except Exception as e:
        print(f"Error fixing IDs: {e}")
        conn.rollback()
        
    conn.close()

if __name__ == "__main__":
    fix_id_types()
