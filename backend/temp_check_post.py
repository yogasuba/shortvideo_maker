import asyncio
import aiohttp
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("POSTIZ_API_KEY")
    base_url = os.getenv("POSTIZ_BASE_URL", "http://localhost:4007/api")
    post_id = "cmlt051780000pj6gz3j0isj8"
    
    # Try the endpoint used in postiz_client.get_post_status (no v1?)
    url = f"{base_url}/public/posts/{post_id}"
    headers = {"Authorization": api_key}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status < 300:
                data = await resp.json()
                # If list, take first item
                post = data[0] if isinstance(data, list) and len(data) > 0 else data
                print(f"ID: {post.get('id')}")
                print(f"State: {post.get('state')}")
                print(f"Error: {post.get('error')}")
                print(f"Message: {post.get('message')}")
            else:
                print(f"Error: {resp.status}")
                print(await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
