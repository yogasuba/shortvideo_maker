import datetime
from datetime import timezone
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Create database directory if it doesn't exist
DB_PATH = "sqlite:///./shortmaker.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Integration(Base):
    __tablename__ = "integrations"
    
    id = Column(String, primary_key=True, index=True) # Unique ID like integration_xxx
    provider = Column(String, default="facebook")
    name = Column(String) # Page name
    internal_id = Column(String, index=True) # Facebook Page ID
    picture = Column(String, nullable=True)
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc), onupdate=lambda: datetime.datetime.now(timezone.utc))

class PostizIntegration(Base):
    __tablename__ = "postiz_integrations"
    
    id = Column(String, primary_key=True)  # From Postiz
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # facebook, instagram, etc.
    enabled = Column(Boolean, default=True)
    last_synced = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    
    id = Column(String, primary_key=True, index=True) # post_xxx
    project_id = Column(String, index=True) # Links to the in-memory/disk project
    integration_id = Column(String, ForeignKey("integrations.id"))
    video_path = Column(String)
    caption = Column(String)
    schedule_time = Column(DateTime(timezone=True), index=True)
    status = Column(String, default="scheduled") # scheduled, posted, failed
    error_message = Column(String, nullable=True)
    fb_post_id = Column(String, nullable=True)
    fb_permalink = Column(String, nullable=True)
    
    # Postiz integration fields
    postiz_post_id = Column(String, nullable=True, index=True)
    postiz_execution_id = Column(String, nullable=True) # For tracking specific execution attempts
    
    # State Machine Status
    # Values: SCHEDULED, PICKUP, UPLOAD, CREATE, MONITOR, COMPLETED, FAILED, SKIPPED_LEGACY
    postiz_status = Column(String, default="SCHEDULED") 
    
    # Error Tracking
    retry_count = Column(Integer, default=0)
    # Values: INTERNAL, NETWORK, POSTIZ, PLATFORM
    error_source = Column(String, nullable=True) 
    last_error_message = Column(String, nullable=True)
    
    postiz_media_id = Column(String, nullable=True)
    postiz_media_url = Column(String, nullable=True) # URL/Path returned by Postiz Upload
    platforms = Column(String, nullable=True)  # Comma-separated platform IDs
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))
    
    integration = relationship("Integration")

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
