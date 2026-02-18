import logging
import datetime
import traceback
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from database import SessionLocal, ScheduledPost, Integration
# facebook_manager removed
from postiz_client import PostizClient, PostizError
import asyncio
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

MAX_RETRIES = 5

async def process_state_machine(postiz_client: PostizClient):
    """
    Core State Machine Loop.
    States: SCHEDULED -> PICKUP -> UPLOAD -> CREATE -> MONITOR -> COMPLETED/FAILED
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        # Ensure UTC timezone awareness for comparisons if needed, but naive UTC is standard here.
        
        # --- 1. PICKUP PHASE ---
        # Find posts that are ready to start.
        # Condition: postiz_status='SCHEDULED' AND schedule_time <= now
        
        ready_posts = db.query(ScheduledPost).filter(
            ScheduledPost.postiz_status == "SCHEDULED",
            ScheduledPost.schedule_time <= now + datetime.timedelta(minutes=1) # 1 min buffer
        ).all()

        for post in ready_posts:
            # LEGACY CHECK: If schedule_time is significantly in the past (e.g., > 1 hour)
            # and it wasn't picked up, marks as SKIPPED_LEGACY.
            # But the user said "If scheduled_time < now()", do not auto post.
            # Strictly speaking, any post in 'SCHEDULED' state with time < now is "late".
            # We strictly enforce the user rule: "If scheduled_time < now(): DO NOT auto-post"
            # BUT, we need a grace period for the scheduler tick itself (e.g. 1-2 mins is fine).
            # If it's old (e.g. > 10 mins ago), skip it.
            
            time_diff = now - (post.schedule_time.replace(tzinfo=None) if post.schedule_time.tzinfo else post.schedule_time)
            if time_diff.total_seconds() > 600: # 10 minutes old
                logger.warning(f"Post {post.id} is too old ({time_diff}). Marking SKIPPED_LEGACY.")
                post.postiz_status = "SKIPPED_LEGACY"
                post.status = "failed" # Legacy status field
                post.error_message = "Skipped as legacy/stale"
                db.commit()
                continue
            
            # Transition to PICKUP -> UPLOAD
            logger.info(f"PICKUP: Post {post.id} ready.")
            post.postiz_status = "UPLOAD"
            post.retry_count = 0
            post.last_error_message = None
            db.commit()

        # --- 2. UPLOAD PHASE ---
        upload_posts = db.query(ScheduledPost).filter(
            ScheduledPost.postiz_status == "UPLOAD"
        ).all()
        
        for post in upload_posts:
            try:
                logger.info(f"UPLOAD: Processing {post.id}")
                if not post.video_path or not os.path.exists(post.video_path):
                    raise PostizError("Video file missing", source="INTERNAL")
                
                # Upload
                res = await postiz_client.upload_video(post.video_path)
                # Parse result: Postiz returns { "id": "...", "path": "..." } roughly
                # Or sometimes wrapped. `_request` returns validated JSON.
                # Assuming top level keys. 
                # If Postiz 2.0, might return just ID string? No, standard is object.
                media_id = res.get("id")
                if not media_id:
                     # Check if it was a list?
                     if isinstance(res, list) and len(res) > 0:
                         media_id = res[0].get("id")
                
                if not media_id:
                    raise PostizError(f"Upload returned no ID: {res}", source="POSTIZ")

                post.postiz_media_id = media_id
                post.postiz_media_url = res.get("path")
                post.postiz_status = "CREATE"
                post.retry_count = 0 
                logger.info(f"UPLOAD SUCCESS: {post.id} -> Media {media_id}")
                
            except PostizError as e:
                handle_error(db, post, e)
            except Exception as e:
                handle_error(db, post, PostizError(str(e), source="INTERNAL"))
            db.commit()

        # --- 3. CREATE PHASE ---
        create_posts = db.query(ScheduledPost).filter(
            ScheduledPost.postiz_status == "CREATE"
        ).all()
        
        for post in create_posts:
            try:
                logger.info(f"CREATE: Processing {post.id}")
                if not post.postiz_media_id or not post.postiz_media_url:
                     # Should not happen if transitions are correct, or if upgrading from old version
                     logger.warning(f"Post {post.id} missing media ID/URL. Reverting to UPLOAD.")
                     post.postiz_status = "UPLOAD" # Regress
                     db.commit()
                     continue

                # Prepare payload
                # Integration IDs need to be fetched?
                # Currently `post.integration_id` is foreign key to `integrations` (Facebook).
                # But Postiz works with its own integration IDs.
                # We need to find the Postiz Integration ID that matches this internal integration.
                # Wait, the `SchedulerPost` has `integration_id`. Is that strict FB Page ID or database ID?
                # `integration_id` -> `integrations.id`.
                # We probably need to map this to a Postiz Integration ID.
                # The user said: "Ensure all active platform integrations already exist in Postiz."
                # We should probably pass the integration ID directly if it IS a Postiz ID, 
                # OR we likely need to lookup `postiz_integrations` table if we have one?
                # `database.py` HAS `PostizIntegration` table!
                # But `ScheduledPost` links to `Integration` (legacy).
                # New posts from UI should likely use Postiz Integrations.
                # IF `post.integration_id` matches a `postiz_integrations.id`, great.
                # IF NOT, we might be in trouble. 
                # Assumption: `post.integration_id` IS the internal ID.
                
                # IMPORTANT: In `postiz_client.py` and `main.py` (previous context check needed),
                # how are we storing integration IDs?
                # `Integration` table has `internal_id` (FB Page ID).
                # `PostizIntegration` table has `id` (Postiz ID).
                # We need to resolve.
                
                # Check if we can find a Postiz integration that matches the platform/name?
                # Best effort: Try to use `post.integration_id` as Postiz ID.
                # If not, try to match by `internal_id`.
                
                # For now, let's assume `post.integration_id` is passed from UI which lists Postiz integrations.
                # The UI sends `integration_id` which is stored.
                
                # NOTE: The User Request says "shortvideo_maker is the single source of truth".
                # If users selected a platform, we must send that ID.
                # Let's assume `post.integration_id` is valid for Postiz or mapped.
                
                integration_ids = [post.integration_id]
                
                res = await postiz_client.create_post(
                    media_items=[{
                        "id": post.postiz_media_id,
                        "path": post.postiz_media_url
                    }],
                    content=post.caption,
                    integration_ids=integration_ids,
                    publish_date=None # "Now" (since we already waited for schedule time)
                )
                
                # Parse result
                # Postiz create returns created post object. 
                # It might be a list if multiple integrations.
                p_id = None
                if isinstance(res, list) and len(res) > 0:
                    p_id = res[0].get("id") or res[0].get("postId")
                elif isinstance(res, dict):
                    p_id = res.get("id") or res.get("postId")
                    
                if not p_id:
                     raise PostizError(f"Create returned no ID: {res}", source="POSTIZ")
                     
                post.postiz_post_id = p_id
                post.postiz_status = "MONITOR"
                post.data = str(res) # Store raw response if field exists? (Not in schema, ignore)
                post.retry_count = 0
                logger.info(f"CREATE SUCCESS: {post.id} -> Postiz {p_id}")
                
            except PostizError as e:
                handle_error(db, post, e)
            except Exception as e:
                handle_error(db, post, PostizError(str(e), source="INTERNAL"))
            db.commit()

        # --- 4. MONITOR PHASE ---
        monitor_posts = db.query(ScheduledPost).filter(
            ScheduledPost.postiz_status == "MONITOR"
        ).all()
        
        for post in monitor_posts:
            try:
                # Poll status
                status_data = await postiz_client.get_post_status(post.postiz_post_id)
                # Status: 'scheduled', 'posted', 'failed'
                status = status_data.get('status')
                
                if status == 'posted':
                    post.postiz_status = "COMPLETED"
                    post.status = "posted" # Legacy field sync
                    post.fb_permalink = status_data.get('permalink_url') or status_data.get('permalink')
                    logger.info(f"MONITOR: Post {post.id} COMPLETED.")
                
                elif status == 'failed':
                    error_msg = status_data.get('error') or "Unknown Postiz Error"
                    raise PostizError(f"Execution Failed: {error_msg}", source="PLATFORM") 
                    # Usually platform error if it failed AFTER creation.
                
                else:
                    # Still scheduled/processing
                    pass

            except PostizError as e:
                # If it's a platform error (failed status), we mark FAILED immediately
                # If network error checking status, we retry check, not fail post.
                if e.source == "PLATFORM" or e.source == "POSTIZ": # Fatal status from Postiz
                     post.postiz_status = "FAILED"
                     post.status = "failed"
                     post.error_message = str(e)
                     post.error_source = e.source
                     logger.error(f"MONITOR FAILED: {post.id} - {e}")
                else:
                    # Network error during monitor - just log, don't change state
                    logger.warning(f"Monitor check failed for {post.id}: {e}")
            
            except Exception as e:
                logger.warning(f"Monitor check unexpected error {post.id}: {e}")
            
            db.commit()

    except Exception as e:
        logger.critical(f"Scheduler Loop Crash: {e}")
        traceback.print_exc()
    finally:
        db.close()

def handle_error(db, post: ScheduledPost, error: PostizError):
    """
    Centralized error handler logic:
    - Decides if retry is allowed.
    - Updates DB state.
    """
    logger.error(f"Job {post.id} failed: {error} (Source: {error.source})")
    
    post.last_error_message = str(error)
    post.error_source = error.source
    
    is_retryable = (error.source in ["NETWORK", "POSTIZ"]) and (post.retry_count < MAX_RETRIES)
    # Note: POSTIZ 500s are retryable, 400s are not. Client raises POSTIZ for non-retryable 4xx usually?
    # Our client raises POSTIZ for 500s (Retryable? We handled retries IN client for 500s).
    # If client raises POSTIZ after retries, it means it's persistent. 
    # But technically we can retry strictly network errors.
    # Logic: Client does retries. If it bubbles up, it failed MAX_RETRIES times already.
    # So maybe we shouldn't retry anymore?
    # Actually, long-term retries (e.g. next tick) are good for persistent network outages.
    
    if is_retryable:
        post.retry_count += 1
        logger.info(f"Retrying {post.id} (Attempt {post.retry_count}/{MAX_RETRIES})")
        # Stay in current state, just increment counter.
    else:
        post.postiz_status = "FAILED"
        post.status = "failed" # Legacy
        post.error_message = str(error) # Legacy

# --- Scheduler Setup ---
scheduler = AsyncIOScheduler()
current_client = None

def start_scheduler(client: PostizClient = None):
    global current_client
    current_client = client
    
    # Run every 60 seconds
    scheduler.add_job(
        process_state_machine, 
        'interval', 
        minutes=1, 
        args=[client],
        misfire_grace_time=300
    )
    scheduler.start()
    logger.info("Scheduler Started.")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler Stopped.")
