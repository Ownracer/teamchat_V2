import sqlite3

def add_deleted_for_column():
    conn = sqlite3.connect('teamchat.db')
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "deletedFor" not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN deletedFor TEXT")
            print("Column 'deletedFor' added successfully.")
        else:
            print("Column 'deletedFor' already exists.")
            
    except Exception as e:
        print(f"Error adding column: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_deleted_for_column()
