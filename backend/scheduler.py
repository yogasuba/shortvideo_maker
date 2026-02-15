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

async def process_scheduled_posts(postiz_client=None):
    """
    Check the database for any posts that need to be published now.
    """
    import sys
    # print(f"[{datetime.datetime.now()}] SCHEDULER TICK: Checking for posts...", flush=True, file=sys.stderr)
    logger.error(f"SCHEDULER TICK: Checking for posts... (UTC: {datetime.datetime.utcnow()})")
    logger.info("Checking for scheduled posts...")
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        
        # 1. PROCESS NEW POSTS (Scheduled -> Processing)
        # Find posts that are scheduled, time has passed, and not yet processed
        print(f"   -> UTC Now (for query): {now}", flush=True)
        # logger.info(f"Current UTC time: {now}")
        
        # DEBUG: Print all scheduled posts first to see what's in DB
        all_scheduled = db.query(ScheduledPost).filter(ScheduledPost.status == "scheduled").all()
        print(f"   -> DEBUG: Total 'scheduled' posts in DB: {len(all_scheduled)}")
        for p in all_scheduled:
             print(f"       - ID: {p.id}, Time: {p.schedule_time} (Naive: {p.schedule_time.replace(tzinfo=None) if p.schedule_time.tzinfo else p.schedule_time}), Due? {p.schedule_time.replace(tzinfo=None) <= now if p.schedule_time.tzinfo else p.schedule_time <= now}")

        new_posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "scheduled",
            ScheduledPost.schedule_time <= now,
            ScheduledPost.postiz_post_id == None
        ).all()
        
        if new_posts:
            msg = f"   -> FOUND {len(new_posts)} POSTS: {[p.id for p in new_posts]}"
            print(msg)
            logger.info(msg)
        else:
            print("   -> No due posts.")
            logger.info("No due posts found.")

        for post in new_posts:
            logger.info(f"Uploading post {post.id} for project {post.project_id}")
            try:
                # Get the integration (page token)
                integration = db.query(Integration).filter(Integration.id == post.integration_id).first()
                if not integration:
                    raise Exception(f"Integration {post.integration_id} not found")

                # Upload to Facebook (Binary Push)
                result = facebook_manager.post_video(
                    page_id=integration.internal_id,
                    page_access_token=integration.access_token,
                    video_path=post.video_path,
                    title=post.caption[:50], 
                    description=post.caption
                )

                # Set to "processing" instead of "posted" immediately
                # Facebook takes time to process the video before it's viewable
                post.status = "processing"
                post.fb_post_id = result.get("id")
                logger.info(f"Upload successful for {post.id}. Status set to 'processing'. FB ID: {post.fb_post_id}")

            except Exception as e:
                logger.error(f"Failed to upload {post.id}: {str(e)}")
                post.status = "failed"
                post.error_message = str(e)
            
            db.commit()

        # 2. POLL FOR COMPLETION (Processing -> Posted/Failed)
        processing_posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "processing",
            ScheduledPost.fb_post_id != None
        ).all()

        for post in processing_posts:
            logger.info(f"Checking processing status for post {post.id} (FB ID: {post.fb_post_id})")
            try:
                integration = db.query(Integration).filter(Integration.id == post.integration_id).first()
                if not integration:
                    continue

                status_data = facebook_manager.get_video_status(post.fb_post_id, integration.access_token)
                
                # Check video_status field inside the status object
                fb_status = status_data.get("status", {})
                video_state = fb_status.get("video_status")
                
                if video_state == "ready":
                    post.status = "posted"
                    post.fb_permalink = status_data.get("permalink_url")
                    logger.info(f"✅ Video {post.id} is now viewable on Facebook!")
                elif video_state == "error":
                    error_msg = fb_status.get("processing_phase", {}).get("errors", ["Unknown Facebook processing error"])[0]
                    post.status = "failed"
                    post.error_message = f"Processing failed: {error_msg}"
                    logger.error(f"❌ Video {post.id} failed processing on Facebook: {error_msg}")
                else:
                    logger.info(f"Still processing {post.id}... (Current state: {video_state})")

            except Exception as e:
                logger.error(f"Error polling status for {post.id}: {e}")
                # Don't change status to failed yet, might be a temporary API error
            
            db.commit()

        # 3. POLL POSTIZ STATUS (Scheduled -> Posted/Failed)
        # Check posts that are managed by Postiz but still marked as 'scheduled' locally
        postiz_posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "scheduled",
            ScheduledPost.postiz_post_id != None
        ).all()

        if postiz_posts:
            print(f"   -> Checking {len(postiz_posts)} Postiz-managed posts...", flush=True)
            
            p_client = postiz_client
            if not p_client:
                # Try to get the initialized client from main
                try:
                    import main
                    p_client = main.postiz_client
                except Exception as e:
                    print(f"   -> Could not import postiz_client: {e}", flush=True)
                    p_client = None

            if p_client:
                for post in postiz_posts:
                    try:
                        p_data = await p_client.get_post(post.postiz_post_id)
                        # Assuming Postiz 2.0 response structure
                        # It might wrap it in 'data' or return directly
                        # Let's verify status.
                        
                        status = p_data.get('status')
                        
                        if status == 'posted':
                            post.status = 'posted'
                            post.fb_permalink = p_data.get('permalink')
                            print(f"   -> Post {post.id} marked as POSTED", flush=True)
                        elif status == 'failed':
                            post.status = 'failed'
                            post.error_message = f"Postiz Error: {p_data.get('error') or 'Check Postiz Dashboard'}"
                            print(f"   -> Post {post.id} marked as FAILED", flush=True)
                        elif status == 'scheduled':
                            print(f"   -> Post {post.id} is still scheduled in Postiz", flush=True)
                        
                    except Exception as e:
                        print(f"   -> Failed to check Postiz status for {post.id}: {e}", flush=True)
                    
                    db.commit()
            else:
                print("   -> Postiz client not available, skipping check.", flush=True)


    except Exception as e:
        import traceback
        print(f"SCHEDULER CRITICAL ERROR: {e}", flush=True, file=sys.stderr)
        traceback.print_exc()
    finally:
        db.close()

# Initialize scheduler
scheduler = AsyncIOScheduler()

def start_scheduler():
    # Run every 1 minute
    scheduler.add_job(process_scheduled_posts, 'interval', minutes=1, misfire_grace_time=None, coalesce=True)
    scheduler.start()
    import sys
    print("SCHEDULER STARTED (interval: 1 minute)", flush=True, file=sys.stderr)
    logger.info("Scheduler started (interval: 1 minute)")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
