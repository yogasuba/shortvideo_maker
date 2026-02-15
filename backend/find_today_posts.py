from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import ScheduledPost
from datetime import datetime, timedelta

engine = create_engine('sqlite:///shortmaker.db')
Session = sessionmaker(bind=engine)
session = Session()

# Define "Today" range broadly (UTC)
now = datetime.utcnow()
start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_day = start_of_day + timedelta(hours=24)

with open("today_posts_output.txt", "w") as f:
    f.write(f"Searching for posts between {start_of_day} and {end_of_day} UTC\n")
    f.write(f"Current UTC: {now}\n")

    posts = session.query(ScheduledPost).filter(
        ScheduledPost.schedule_time >= start_of_day,
        ScheduledPost.schedule_time <= end_of_day
    ).all()

    f.write(f"Found {len(posts)} posts:\n")
    for post in posts:
        f.write(f"--- ID: {post.id} ---\n")
        f.write(f"Time (UTC Naive): {post.schedule_time}\n")
        f.write(f"Status: {post.status}\n")
        f.write(f"Postiz ID: {post.postiz_post_id}\n")
        
        # Check if due
        is_due = post.schedule_time <= now
        f.write(f"Due? {is_due}\n")
        
        # Check if Postiz ID is present (Manual scheduler ignores these)
        has_postiz = post.postiz_post_id is not None
        f.write(f"Handled by Postiz? {has_postiz}\n")
