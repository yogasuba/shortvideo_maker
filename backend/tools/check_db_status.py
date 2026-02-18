
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database import Integration, ScheduledPost
import datetime

DB_PATH = "sqlite:///./shortmaker.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine)

def check_status():
    db = SessionLocal()
    try:
        # Check Integrations
        print("--- INTEGRATIONS ---")
        integrations = db.query(Integration).all()
        if not integrations:
            print("No integrations found. You need to connect a Facebook Page first.")
        else:
            for i in integrations:
                print(f"ID: {i.id}, Name: {i.name}, Provider: {i.provider}, Active: {i.is_active}")
                if not i.access_token:
                    print(f"  WARNING: No access token for {i.name}")

        # Check Pending Posts
        print("\n--- PENDING/FAILED POSTS ---")
        posts = db.query(ScheduledPost).filter(
            ScheduledPost.status.in_(["scheduled", "failed_retry", "processing"])
        ).all()
        
        if not posts:
            print("No pending posts in the queue.")
        else:
            for p in posts:
                print(f"Post {p.id}: Status={p.status}, Schedule={p.schedule_time}, Retry={p.retry_count}")
                if p.integration_id:
                     print(f"  Target Integration: {p.integration_id}")
                else:
                     print(f"  WARNING: No Integration ID (Postiz managed?)")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_status()
