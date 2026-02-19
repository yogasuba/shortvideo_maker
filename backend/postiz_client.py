import aiohttp
import aiofiles
import os
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone
import asyncio
import json

logger = logging.getLogger(__name__)

class PostizError(Exception):
    def __init__(self, message, source="POSTIZ", raw_error=None):
        super().__init__(message)
        self.source = source # INTERNAL, NETWORK, POSTIZ, PLATFORM
        self.raw_error = raw_error

class PostizClient:
    def __init__(self, api_key: str, base_url: str, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": self.api_key},
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
             self.session = aiohttp.ClientSession(
                headers={"Authorization": self.api_key},
                timeout=aiohttp.ClientTimeout(total=60)
            )
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request with robust retry logic and error normalization"""
        url = f"{self.base_url}{endpoint}"
        await self._ensure_session()
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Use existing session or create temporary one if context manager wasn't used
                # But _ensure_session handles the persistent one.
                # If we are not in context manager, self.session might be unclosed if we don't close it manually.
                # Ideally caller ensures lifecycle.
                
                async with self.session.request(method, url, **kwargs) as resp:
                    if resp.status < 400:
                        try:
                            return await resp.json()
                        except:
                            return await resp.text()
                            
                    # Error handling
                    text = await resp.text()
                    try:
                        error_json = json.loads(text)
                        error_msg = error_json.get('message') or error_json.get('error') or text
                    except:
                        error_msg = text

                    if resp.status in [401, 403]:
                        raise PostizError(f"Authentication failed: {error_msg}", source="INTERNAL")
                    
                    if resp.status == 429:
                        # Rate limit - wait and retry
                        wait_time = float(resp.headers.get("Retry-After", 2 ** attempt))
                        logger.warning(f"Rate limited. Waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    if resp.status >= 500:
                        # Server error - retryable
                        logger.warning(f"Postiz Server Error {resp.status}: {error_msg}")
                        if attempt < self.max_retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise PostizError(f"Postiz Server Error: {error_msg}", source="POSTIZ")
                        
                    # 4xx errors (Validation etc) - usually not retryable
                    raise PostizError(f"Postiz Validation Error: {error_msg}", source="POSTIZ", raw_error=text)

            except aiohttp.ClientError as e:
                last_exception = e
                logger.warning(f"Network error (attempt {attempt+1}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise PostizError(f"Network Error: {str(e)}", source="NETWORK")
            except Exception as e:
                # Unexpected logic error
                raise PostizError(f"Internal Client Error: {str(e)}", source="INTERNAL")
                
        raise PostizError(f"Max retries exceeded: {str(last_exception)}", source="NETWORK")
    
    async def upload_video(self, video_path: str) -> Dict:
        """Upload video file with validation"""
        if not os.path.exists(video_path):
            raise PostizError(f"Video file not found: {video_path}", source="INTERNAL")

        # Size check (optional, but good for debugging)
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"Uploading video: {video_path} ({size_mb:.2f} MB)")

        try:
            async with aiofiles.open(video_path, 'rb') as f:
                content = await f.read()
                data = aiohttp.FormData()
                data.add_field('file',
                              content,
                              filename=os.path.basename(video_path),
                              content_type='video/mp4')
                
                # Using a longer timeout for uploads
                return await self._request('POST', '/public/v1/upload', data=data)
        except PostizError:
            raise
        except Exception as e:
            raise PostizError(f"Upload Failed: {str(e)}", source="INTERNAL")

    async def create_post(
        self,
        media_items: List[Dict],
        content: str,
        integration_ids: List[str],
        publish_date: Optional[datetime] = None
    ) -> Dict:
        """
        Create a post in Postiz.
        Returns the simplified response with ID or raises PostizError.
        """
        if not integration_ids:
             raise PostizError("No integration IDs provided", source="INTERNAL")
             
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
                            # Ensure we just pass what Postiz expects (id or path)
                            # Assuming media_items contain objects returned from upload_video
                            # Postiz usually expects { "id": "..." } for uploaded media
                            {
                                "id": item.get("id"),
                                "path": item.get("path")
                            } for item in media_items if item.get("id")
                        ]
                    }
                ],
                "settings": {} 
            })

        # Calculate accurate ISO format
        # If publish_date is none, we still send "now" type but maybe date is ignored?
        # Safe to send current UTC for 'now'
        date_iso = (publish_date.astimezone(timezone.utc) if publish_date else datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")

        payload = {
            "type": "now" if not publish_date else "schedule",
            "shortLink": False,
            "date": date_iso,
            "tags": [],
            "posts": posts
        }
        
        logger.info(f"Creating Postiz Post: {len(integration_ids)} integrations, Date: {date_iso}")
        
        try:
            response = await self._request('POST', '/public/v1/posts', json=payload)
            # Response might be a list of created posts or a single object?
            # Usually Postiz 2.0 returns the Created Post object(s).
            # We normalized references to just return the response data.
            return response
        except PostizError:
            raise
        except Exception as e:
             raise PostizError(f"Failed to build/send post: {str(e)}", source="INTERNAL")
    
    async def get_post_status(self, post_id: str) -> Dict:
        """
        Get normalized status of a post.
        """
        try:
            # Public API returns a list [ { ... } ] usually for search, but 'posts/{id}' might be single object.
            # Client implementation showed getting [0].
            res = await self._request('GET', f'/public/posts/{post_id}')
            data = res[0] if isinstance(res, list) and len(res) > 0 else res
            
            if not data:
                 raise PostizError("Post not found", source="POSTIZ")
                 
            return data
        except PostizError:
            raise
        except Exception as e:
            raise PostizError(f"Status Check Failed: {str(e)}", source="NETWORK")

    async def get_integrations(self) -> List[Dict]:
        try:
            # Debug API Key
            masked_key = self.api_key[:10] + "..." if self.api_key else "None"
            logger.info(f"Fetching integrations with API Key: {masked_key} from {self.base_url}")
            response = await self._request('GET', '/public/v1/integrations')
            
            if response:
                platform_map = {
                    'facebook': 'facebook', 'instagram': 'instagram', 'tiktok': 'tiktok',
                    'youtube': 'youtube', 'twitter': 'twitter', 'x': 'twitter',
                    'linkedin': 'linkedin', 'threads': 'threads', 'pinterest': 'pinterest',
                    'discord': 'discord', 'slack': 'slack', 'reddit': 'reddit'
                }
                
                for integration in response:
                    raw_type = str(integration.get('type', '')).lower()
                    provider_id = str(integration.get('identifier') or integration.get('providerIdentifier') or '').lower()
                    platform = 'unknown'
                    
                    if raw_type in platform_map:
                        platform = platform_map[raw_type]
                    elif provider_id:
                        for key, val in platform_map.items():
                            if key in provider_id:
                                platform = val
                                break
                    
                    integration['platform'] = platform
                    if integration.get('type') == 'unknown' or not integration.get('type'):
                        integration['type'] = platform
                        
            return response
        except Exception as e:
             # This is often critical for UI, so we log heavily
             logger.error(f"Failed to fetch integrations: {e}")
             raise PostizError(f"Fetch Integrations Failed: {str(e)}", source="NETWORK")

    async def delete_integration(self, integration_id: str) -> Dict:
        """Delete an integration from Postiz"""
        try:
            return await self._request('DELETE', f'/public/v1/integrations/{integration_id}')
        except Exception as e:
             logger.error(f"Failed to delete integration {integration_id}: {e}")
             raise PostizError(f"Delete Integration Failed: {str(e)}", source="NETWORK")
    
    async def close(self):
        if self.session:
            await self.session.close()
