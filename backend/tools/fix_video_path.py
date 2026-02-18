from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import ScheduledPost
import json
from pathlib import Path

DB_PATH = "sqlite:///./shortmaker.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()
post = db.query(ScheduledPost).filter(ScheduledPost.id == "post_d21265bf").first()

if post:
    print(f"Post: {post.id}")
    print(f"Project ID: {post.project_id}")
    print(f"Video Path: {post.video_path}")
    print(f"Media URL: {post.media_url}")
    
    # Load projects.json to find the video path
    projects_file = Path("storage/projects.json")
    if projects_file.exists():
        with open(projects_file, 'r') as f:
            projects = json.load(f)
        
        if post.project_id in projects:
            project = projects[post.project_id]
            video_path = project.get('video_path')
            print(f"\nFound video in project: {video_path}")
            
            if video_path and not post.video_path:
                print(f"Updating post with video_path...")
                post.video_path = video_path
                post.status = 'scheduled'  # Reset to scheduled
                post.retry_count = 0  # Reset retry count
                post.next_retry_at = None
                post.error_message = None
                db.commit()
                print("Done! Post updated and ready for processing.")
        else:
            print(f"Project {post.project_id} not found in projects.json")
    else:
        print("projects.json not found")
else:
    print("Post not found")

db.close()
