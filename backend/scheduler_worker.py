import time
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, ScheduledPost, Integration
from facebook_manager import facebook_manager
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scheduler_worker.log")
    ]
)
logger = logging.getLogger("scheduler_worker")

def get_now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def calculate_backoff(retry_count):
    # 1m -> 5m -> 15m -> 1h -> 6h
    backoffs = [1, 5, 15, 60, 360]
    index = min(retry_count, len(backoffs) - 1)
    return datetime.timedelta(minutes=backoffs[index])

def reset_stale_jobs(db: Session):
    """
    Step 1: Crash Recovery
    If status = processing AND processing_started_at < now - 10 minutes -> Reset to scheduled
    """
    ten_minutes_ago = get_now_utc() - datetime.timedelta(minutes=10)
    stale_jobs = db.query(ScheduledPost).filter(
        ScheduledPost.status == "processing",
        ScheduledPost.processing_started_at < ten_minutes_ago
    ).all()
    
    for job in stale_jobs:
        logger.warning(f"Resetting stale job {job.id} (started at {job.processing_started_at})")
        job.status = "scheduled"
        job.processing_started_at = None
    
    if stale_jobs:
        db.commit()

def fetch_due_jobs(db: Session):
    """
    Step 2: Fetch Due Jobs
    """
    now = get_now_utc()
    return db.query(ScheduledPost).filter(
        (
            (ScheduledPost.status == "scheduled") & 
            (ScheduledPost.schedule_time <= now)
        ) |
        (
            (ScheduledPost.status == "failed_retry") & 
            (ScheduledPost.next_retry_at <= now)
        )
    ).all()

def process_job(db: Session, job: ScheduledPost):
    """
    Step 3-6: Atomic Lock, Publish, Idempotency, and Retry Logic
    """
    # SKIP Postiz-managed jobs (they are scheduled on Postiz side)
    if job.postiz_post_id or not job.integration_id:
        logger.info(f"Skipping job {job.id} (Postiz managed or missing integration_id)")
        print(f"DEBUG: SKIPPING {job.id} (PostizID: {job.postiz_post_id}, IntID: {job.integration_id})")
        return

    # Step 3: Atomic Lock (check status again to be absolutely sure)
    # In SQLite, we don't have true row-level locking for updates like PG, 
    # but we can check if it's still in a state we can process.
    try:
        print(f"DEBUG: Checking status for {job.id} (Current: {job.status})")
        if job.status not in ["scheduled", "failed_retry"]:
            logger.info(f"Skipping job {job.id} (already locked/processed)")
            print(f"DEBUG: Skipping {job.id} - status {job.status}")
            return

        job.status = "processing"
        job.processing_started_at = get_now_utc()
        db.commit()
        print(f"DEBUG: Locked job {job.id}")
        
        # Step 4: Publish
        logger.info(f"Processing job {job.id} for integration {job.integration_id}")
    except Exception as e:
        # If locking fails (e.g., race condition where another worker processed it)
        logger.warning(f"Failed to acquire lock for job {job.id}: {e}")
        db.rollback() # Rollback any changes if commit failed
        return
    
    try:
        # Step 6: Idempotency Protection
        if job.fb_post_id:
            logger.info(f"Job {job.id} already has fb_post_id {job.fb_post_id}. Checking status...")
            # We could check FB API here, but for now we'll assume if it has an ID, we should check if it's 'posted'
            # In our case, if it has an ID but wasn't marked 'posted', it might have crashed.
            # Let's try to verify it.
            # (Omitted FB verification for simplicity, but logic could go here)
            pass

        # Get Integration
        integration = db.query(Integration).filter(Integration.id == job.integration_id).first()
        if not integration:
            raise Exception(f"Integration {job.integration_id} not found")

        # Step 5: Facebook Publishing Logic
        # (Token validation would ideally be here or inside post_video)
        
        # Determine paths
        video_path = job.video_path or job.media_url
        if not video_path:
             raise Exception("No video path or media url found")
             
        if not os.path.exists(video_path):
             raise Exception(f"File not found: {video_path}")

        result = facebook_manager.post_video(
            page_id=integration.internal_id,
            page_access_token=integration.access_token,
            video_path=video_path,
            title=job.caption[:50],
            description=job.caption
        )

        job.status = "posted"
        job.fb_post_id = result.get("id")
        logger.info(f"Successfully posted job {job.id}. FB ID: {job.fb_post_id}")

    except Exception as e:
        error_str = str(e)
        logger.error(f"Error processing job {job.id}: {error_str}")
        
        # Determine if error is permanent or transient
        # Common permanent errors: 400 (Bad Request/Permissions), 401 (Unauthorized), 403 (Forbidden)
        is_permanent = False
        if "401" in error_str or "403" in error_str or "permission" in error_str.lower():
            is_permanent = True
            
        if is_permanent:
            job.status = "failed_permanent"
            job.error_message = f"Permanent Error: {error_str}"
        else:
            # Transient error - retry
            job.retry_count += 1
            if job.retry_count > 5:
                job.status = "failed_permanent"
                job.error_message = f"Max retries exceeded: {error_str}"
            else:
                job.status = "failed_retry"
                job.next_retry_at = get_now_utc() + calculate_backoff(job.retry_count - 1)
                job.error_message = f"Retry {job.retry_count}: {error_str}"
                logger.info(f"Job {job.id} scheduled for retry at {job.next_retry_at}")
    
    db.commit()

def main():
    logger.info("Scheduler worker started (Postiz-level architecture)")
    while True:
        db = SessionLocal()
        try:
            # Step 1: Crash Recovery
            reset_stale_jobs(db)
            
            # Step 2: Fetch Due Jobs
            due_jobs = fetch_due_jobs(db)
            
            if due_jobs:
                logger.info(f"Found {len(due_jobs)} due jobs")
                print(f"DEBUG: Found {len(due_jobs)} due jobs")
                for job in due_jobs:
                    print(f"DEBUG: Processing job {job.id}")
                    process_job(db, job)
            
        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
        finally:
            db.close()
        
        time.sleep(10) # Poll every 10 seconds

if __name__ == "__main__":
    main()
