from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import os
import datetime

DB_PATH = "sqlite:///c:/Users/jayas/Desktop/postizshortmaker/shortvideo_maker/backend/shortmaker.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

print("--- Scheduled Posts ---")
try:
    result = session.execute(text("SELECT id, schedule_time, status, postiz_status, retry_count, error_source, last_error_message, postiz_post_id FROM scheduled_posts ORDER BY created_at DESC LIMIT 10"))
    for row in result:
        print(row)
except Exception as e:
    print(f"Error reading scheduled_posts: {e}")

print("\n--- Integrations ---")
try:
    result = session.execute(text("SELECT id, provider, name, internal_id FROM integrations"))
    for row in result:
        print(row)
except Exception as e:
    print(f"Error reading integrations: {e}")

print("\n--- Postiz Integrations ---")
try:
    result = session.execute(text("SELECT id, name, platform, enabled FROM postiz_integrations"))
    for row in result:
        print(row)
except Exception as e:
    print(f"Error reading postiz_integrations: {e}")
