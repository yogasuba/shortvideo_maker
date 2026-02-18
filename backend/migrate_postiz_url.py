import sqlite3

def migrate():
    try:
        conn = sqlite3.connect("shortmaker.db")
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(scheduled_posts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "postiz_media_url" not in columns:
            print("Adding postiz_media_url column...")
            cursor.execute("ALTER TABLE scheduled_posts ADD COLUMN postiz_media_url VARCHAR")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
