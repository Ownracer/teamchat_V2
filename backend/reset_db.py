import psycopg2
from database import get_db_connection, init_db

def reset_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("WARNING: This will DROP all data in tables: users, chats, messages, ideas.")
    
    try:
        tables = ["users", "chats", "messages", "ideas"]
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"Dropped table {table}")
            
        conn.commit()
        print("All tables dropped.")
        
        # Re-initialize
        print("Re-initializing tables...")
        init_db()
        print("Database Reset Complete.")
        
    except Exception as e:
        print(f"Error resetting DB: {e}")
        conn.rollback()
        
    conn.close()

if __name__ == "__main__":
    reset_database()
