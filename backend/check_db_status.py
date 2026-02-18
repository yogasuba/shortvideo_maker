import sqlite3
import datetime
from datetime import timezone

def check_db():
    conn = sqlite3.connect("shortmaker.db")
    cursor = conn.cursor()
    
    print(f"Current System Time (Local): {datetime.datetime.now()}")
    print(f"Current UTC Time: {datetime.datetime.utcnow()}")
    
    print("-" * 50)
    cursor.execute("SELECT id, schedule_time, postiz_status, status, error_message, created_at, postiz_post_id FROM scheduled_posts ORDER BY created_at DESC LIMIT 1")
    rows = cursor.fetchall()
    
    import requests
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("POSTIZ_API_KEY")
    base_url = os.getenv("POSTIZ_BASE_URL", "http://localhost:4007/api")
    
    with open("status.txt", "w") as f:
        f.write(f"Current System Time (Local): {datetime.datetime.now()}\n")
        f.write(f"Current UTC Time: {datetime.datetime.utcnow()}\n")
        f.write("-" * 50 + "\n")
        
        for row in rows:
            p_id, sched_time, p_status, status, err, created, postiz_id = row
            f.write(f"ID: {p_id}\n")
            f.write(f"  Schedule Time (DB): {sched_time}\n")
            f.write(f"  Postiz Status (DB): {p_status}\n")
            f.write(f"  Legacy Status: {status}\n")
            f.write(f"  Postiz ID: {postiz_id}\n")
            f.write(f"  Error: {err}\n")
            
            if postiz_id:
                 try:
                     r = requests.get(f"{base_url}/public/posts/{postiz_id}", headers={"Authorization": api_key})
                     f.write(f"  [API] Status Code: {r.status_code}\n")
                     f.write(f"  [API] Body: {r.text}\n")
                 except Exception as e:
                     f.write(f"  [API] Request Failed: {e}\n")
            
            f.write("-" * 20 + "\n")
        
    conn.close()

if __name__ == "__main__":
    check_db()
