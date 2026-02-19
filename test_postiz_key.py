import asyncio
import aiohttp
import os
import sys

# Load env manually to ensure we use the file on disk
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

POSTIZ_URL = os.getenv("POSTIZ_BASE_URL", "http://localhost:4007/api")
API_KEY = os.getenv("POSTIZ_API_KEY")

async def check_api_key():
    print(f"Checking API Key against {POSTIZ_URL}...")
    
    if not API_KEY:
        print("CRITICAL: POSTIZ_API_KEY is missing from environment!")
        return False
        
    print(f"Key Preview: {API_KEY[:20]}...")
    
    # Use Raw Key for Shared Secret Auth
    headers = {"Authorization": API_KEY}
    
    endpoints = ["/users/me", "/integrations"]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            # Construct URL correctly using base (which includes /api)
            # If base="http://localhost:4007/api", we want "http://localhost:4007/api/users/me"
            # But wait, endpoint has leading slash.
            
            clean_base = POSTIZ_URL.rstrip('/')
            
            if endpoint == "/integrations":
                 # Public API might be at /api/public/v1/integrations or just /api/integrations?
                 # Let's try /api/integrations first as that's what Nginx proxies to /integrations
                 test_url = f"{clean_base}{endpoint}"
            else:
                 test_url = f"{clean_base}{endpoint}"

            print(f"Testing URL: {test_url}")
            try:
                async with session.get(test_url, headers=headers) as resp:
                    if resp.status == 200:
                        print("API Key is VALID! (200 OK)")
                        try:
                            data = await resp.json()
                            print(f"Data received: {len(data)} items found.")
                        except:
                            print("Response Text:", await resp.text())
                        return True
                    else:
                        print(f"API returned {resp.status}")
                        print("Response:", await resp.text())
            except Exception as e:
                print(f"Connection Error: {e}")
                
    return False

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_api_key())
