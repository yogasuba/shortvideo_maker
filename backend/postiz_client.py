import aiohttp
import aiofiles
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import asyncio
import json

logger = logging.getLogger(__name__)

class PostizClient:
    def __init__(self, api_key: str, base_url: str, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": self.api_key}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                if self.session is None:
                    # Fallback if context manager not used
                    async with aiohttp.ClientSession(
                        headers={"Authorization": self.api_key}
                    ) as session:
                         async with session.request(method, url, **kwargs) as resp:
                            if resp.status >= 400:
                                text = await resp.text()
                                logger.error(f"API Error {resp.status}: {text}")
                                resp.raise_for_status()
                            return await resp.json()

                async with self.session.request(method, url, **kwargs) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        logger.error(f"API Error {resp.status}: {text}")
                        resp.raise_for_status()
                    return await resp.json()

            except aiohttp.ClientError as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def upload_video(self, video_path: str) -> Dict:
        """Upload video file to Postiz"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        async with aiofiles.open(video_path, 'rb') as f:
            content = await f.read()
            data = aiohttp.FormData()
            data.add_field('file',
                          content,
                          filename=os.path.basename(video_path),
                          content_type='video/mp4')
            
            return await self._request('POST', '/public/v1/upload', data=data)
    
    async def upload_video_from_url(self, video_url: str) -> Dict:
        """Upload video from URL"""
        payload = {"url": video_url}
        return await self._request('POST', '/public/v1/upload-from-url', json=payload)
    
    async def create_post(
        self,
        media_items: List[Dict],
        content: str,
        integration_ids: List[str],
        publish_date: Optional[datetime] = None
    ) -> Dict:
        """Schedule a post in Postiz"""
        
        # Build the posts array - each platform gets its own post object in Postiz 2.0
        posts = []
        for i_id in integration_ids:
            posts.append({
                "integration": {
                    "id": i_id
                },
                "value": [
                    {
                        "content": content,
                        "image": [
                            {
                                "id": item.get("id"),
                                "path": item.get("path")
                            } for item in media_items if item.get("id") and item.get("path")
                        ]
                    }
                ],
                "settings": {} # Will be mapped by Postiz server
            })

        payload = {
            "type": "now" if not publish_date else "schedule",
            "shortLink": False,
            "date": (publish_date.astimezone(timezone.utc) if publish_date else datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z"),
            "tags": [],
            "posts": posts
        }
        
        logging.info(f"Postiz Payload: {json.dumps(payload, indent=2)}")

        return await self._request('POST', '/public/v1/posts', json=payload)
    
    async def get_integrations(self) -> List[Dict]:
        """Fetch connected social media accounts with platform mapping"""
        response = await self._request('GET', '/public/v1/integrations')
        
        if response:
            # Map integration types to platform names
            platform_map = {
                'facebook': 'facebook',
                'instagram': 'instagram',
                'tiktok': 'tiktok',
                'youtube': 'youtube',
                'twitter': 'twitter',
                'x': 'twitter',
                'linkedin': 'linkedin',
                'threads': 'threads',
                'pinterest': 'pinterest',
                'discord': 'discord',
                'slack': 'slack',
                'reddit': 'reddit'
            }
            
            for integration in response:
                # Extract potential platform identifiers
                raw_type = str(integration.get('type', '')).lower()
                # Public API uses 'identifier', but internal might use 'providerIdentifier'
                provider_id = str(integration.get('identifier') or integration.get('providerIdentifier') or '').lower()
                
                # Determine platform
                platform = 'unknown'
                
                # Check type first
                if raw_type in platform_map:
                    platform = platform_map[raw_type]
                # Check providerIdentifier (often contains the platform name like 'facebook-page')
                elif provider_id:
                    for key, val in platform_map.items():
                        if key in provider_id:
                            platform = val
                            break
                
                # Assign standardized platform
                integration['platform'] = platform
                
                # Ensure type is set for main.py compatibility if it was missing/unknown
                if integration.get('type') == 'unknown' or not integration.get('type'):
                    integration['type'] = platform
                    
        return response
    
    async def get_post_status(self, post_id: str) -> Dict:
        """Get status of a scheduled post"""
        # Public API returns a list [ { ... } ]
        res = await self._request('GET', f'/public/posts/{post_id}')
        return res[0] if isinstance(res, list) and len(res) > 0 else res

    async def get_post(self, post_id: str) -> Dict:
        """Get a single post by ID"""
        # Public API returns a list [ { ... } ]
        res = await self._request('GET', f'/public/posts/{post_id}')
        return res[0] if isinstance(res, list) and len(res) > 0 else res
    
    async def get_all_posts(self) -> List[Dict]:
        """Get all posts"""
        return await self._request('GET', '/public/v1/posts')
    
    async def delete_post(self, post_id: str) -> Dict:
        """Delete a scheduled post"""
        return await self._request('DELETE', f'/public/v1/posts/{post_id}')
    
    async def close(self):
        if self.session:
            await self.session.close()
