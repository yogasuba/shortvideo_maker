from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import PostizIntegration, ScheduledPost
import requests
import os

DB_PATH = "sqlite:///./shortmaker.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine)

# Sync the new integration from Postiz
print("Syncing Postiz integrations...")
db = SessionLocal()

POSTIZ_URL = os.getenv("POSTIZ_BASE_URL", "http://localhost:4200")
POSTIZ_KEY = os.getenv("POSTIZ_API_KEY")

headers = {"Authorization": f"Bearer {POSTIZ_KEY}"}
response = requests.get(f"{POSTIZ_URL}/integrations", headers=headers)

if response.status_code == 200:
    integrations = response.json().get("data", [])
    print(f"Found {len(integrations)} Postiz integrations")
    
    for integ in integrations:
        existing = db.query(PostizIntegration).filter(PostizIntegration.id == integ["id"]).first()
        if existing:
            existing.name = integ["name"]
            existing.platform = integ.get("platform", integ.get("type", "unknown"))
            print(f"Updated: {integ['id']} ({integ['name']})")
        else:
            new_integ = PostizIntegration(
                id=integ["id"],
                name=integ["name"],
                platform=integ.get("platform", integ.get("type", "unknown"))
            )
            db.add(new_integ)
            print(f"Added: {integ['id']} ({integ['name']})")
    
    db.commit()
    
    # Now update the stuck post
    post = db.query(ScheduledPost).filter(ScheduledPost.id == "post_d21265bf").first()
    if post:
        # Find the Facebook integration
        fb_integ = [i for i in integrations if i.get("platform") == "facebook" or i.get("type") == "facebook"]
        if fb_integ:
            new_postiz_id = fb_integ[0]["id"]
            print(f"\nUpdating post {post.id}:")
            print(f"  New Postiz Integration ID: {new_postiz_id}")
            post.postiz_post_id = new_postiz_id  # Link to Postiz integration
            post.status = 'scheduled'
            post.retry_count = 0
            post.next_retry_at = None
            post.error_message = None
            db.commit()
            print("✓ Post updated and reset to 'scheduled'")
            print("  Worker will process it within 10 seconds!")
        else:
            print("ERROR: No Facebook integration found")
    else:
        print("Post not found")
else:
    print(f"Failed to fetch integrations: {response.status_code}")

db.close()
