
import sys
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, ScheduledPost, Integration

DB_PATH = "sqlite:///./shortmaker.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine)

def check_system():
    now_utc = datetime.datetime.utcnow()
    now_local = datetime.datetime.now()
    
    print(f"--- TIME CHECK ---")
    print(f"Server UTC Time:   {now_utc}")
    print(f"Server Local Time: {now_local}")
    print(f"------------------\n")
    
    db = SessionLocal()
    try:
        # Check all scheduled posts
        all_posts = db.query(ScheduledPost).all()
        print(f"Total Posts in DB: {len(all_posts)}")
        
        scheduled = [p for p in all_posts if p.status == "scheduled"]
        print(f"Scheduled Posts: {len(scheduled)}")
        
        for p in scheduled:
            diff = p.schedule_time - now_utc
            is_due = p.schedule_time <= now_utc
            print(f"  - ID: {p.id}")
            print(f"    Schedule Time (UTC): {p.schedule_time}")
            print(f"    Due Now? {'YES' if is_due else 'NO'} (Time until due: {diff})")
            print(f"    Integration ID: {p.integration_id}")
            print(f"    Postiz ID: {p.postiz_post_id}")
            
        processing = [p for p in all_posts if p.status == "processing"]
        if processing:
            print(f"\nProcessing Posts: {len(processing)}")
            for p in processing:
                print(f"  - ID: {p.id}, FB ID: {p.fb_post_id}")
                
        failed = [p for p in all_posts if p.status == "failed"]
        if failed:
            print(f"\nFailed Posts: {len(failed)}")
            for p in failed:
                print(f"  - ID: {p.id}, Error: {p.error_message}")

    finally:
        db.close()

if __name__ == "__main__":
    check_system()
