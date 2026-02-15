import asyncio
import logging
import sys
# Configure logging so we can see output
logging.basicConfig(level=logging.INFO)

# Redirect stdout/stderr to file
log_file = open("manual_trigger_log.txt", "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# Make sure we can import local modules
from scheduler import process_scheduled_posts
from database import init_db
import main
from postiz_client import PostizClient
from main import Config

async def main():
    print("Initializing DB...", flush=True)
    init_db()
    
    # Initialize Postiz Client for the scheduler to use
    if Config.POSTIZ_ENABLED and Config.POSTIZ_API_KEY:
        print("Initializing Postiz Client...", flush=True)
        main.postiz_client = PostizClient(
             api_key=Config.POSTIZ_API_KEY,
             base_url=Config.POSTIZ_BASE_URL
        )
        await main.postiz_client.__aenter__()
    
    print("Running process_scheduled_posts...", flush=True)
    
    # Debug: List all posts from Postiz
    try:
        print("Debugging: Fetching all posts from Postiz...", flush=True)
        all_posts = await main.postiz_client.get_all_posts()
        print(f"Postiz has {len(all_posts)} posts.", flush=True)
        for p in all_posts: # Print first few or all IDs
             print(f" - Found Postiz Post: {p.get('id')} status={p.get('status')}", flush=True)
    except Exception as e:
        print(f"Failed to list posts: {e}", flush=True)

    try:
        await process_scheduled_posts(postiz_client=main.postiz_client)
        print("Success! Scheduler job completed.", flush=True)
    except Exception as e:
        print(f"Error running scheduler job: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if main.postiz_client:
            await main.postiz_client.close()

if __name__ == "__main__":
    asyncio.run(main())
