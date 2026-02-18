from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import ScheduledPost

engine = create_engine('sqlite:///shortmaker.db')
Session = sessionmaker(bind=engine)
session = Session()

posts = session.query(ScheduledPost).all()
print(f"Total posts: {len(posts)}")
for p in posts:
    print(f"ID: {p.id}, Time: {p.schedule_time}, Caption: {p.caption[:20]}")
