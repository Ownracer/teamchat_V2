import psycopg2
from database import get_db_connection

def inspect_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("--- Checking 'users' table schema ---")
    try:
        # Get column details
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[0]}, Type: {col[1]}")
            
        # Check row count
        cursor.execute("SELECT count(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"\nRow confirm: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    inspect_users()
