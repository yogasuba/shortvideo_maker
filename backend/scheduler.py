import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from database import SessionLocal, ScheduledPost, Integration
from facebook_manager import facebook_manager
import asyncio
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

async def process_scheduled_posts():
    """
    Check the database for any posts that need to be published now.
    """
    logger.info("Checking for scheduled posts...")
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        # Find posts that are scheduled, time has passed, and not yet processed
        posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "scheduled",
            ScheduledPost.schedule_time <= now
        ).all()

        for post in posts:
            logger.info(f"Processing post {post.id} for project {post.project_id}")
            try:
                # 1. Get the integration (page token)
                integration = db.query(Integration).filter(Integration.id == post.integration_id).first()
                if not integration:
                    raise Exception(f"Integration {post.integration_id} not found")

                # 2. Upload to Facebook
                # We use the video title as the title and caption as the description
                # Assuming caption stores what the user wants as the post body
                result = facebook_manager.post_video(
                    page_id=integration.internal_id,
                    page_access_token=integration.access_token,
                    video_path=post.video_path,
                    title=post.caption[:50], # Facebook title is short
                    description=post.caption
                )

                # 3. Update status on success
                post.status = "posted"
                post.fb_post_id = result.get("id")
                post.fb_permalink = f"https://www.facebook.com/{result.get('id')}"
                logger.info(f"Successfully posted {post.id} to Facebook")

            except Exception as e:
                logger.error(f"Failed to post {post.id}: {str(e)}")
                post.status = "failed"
                post.error_message = str(e)
            
            db.commit()

    finally:
        db.close()

# Initialize scheduler
scheduler = AsyncIOScheduler()

def start_scheduler():
    # Run every 1 minute
    scheduler.add_job(process_scheduled_posts, 'interval', minutes=1)
    scheduler.start()
    logger.info("Scheduler started (interval: 1 minute)")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
