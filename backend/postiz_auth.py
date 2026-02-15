import os
import subprocess
import jwt
import datetime
import logging
import aiohttp
import asyncio
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class PostizAuthService:
    def __init__(self, base_url: str, jwt_secret: str):
        self.base_url = base_url.rstrip('/')
        self.jwt_secret = jwt_secret
        self.user_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    def get_user_id(self) -> Optional[str]:
        """Fetch User ID from Postiz Docker Container if not already cached"""
        if self.user_id:
            return self.user_id

        logger.info("Attempting to fetch Postiz User ID from Docker...")
        try:
            # Assuming 'postiz-postgres' is the container name as per docker-compose
            cmd = [
                "docker", "exec", "postiz-postgres", 
                "psql", "-U", "postiz-user", "-d", "postiz-db-local", 
                "-t", "-A", "-F", "|", "-c", 
                "SELECT u.id, u.email, uo.\"organizationId\" FROM \"User\" u JOIN \"UserOrganization\" uo ON u.id = uo.\"userId\" LIMIT 1;"
            ]
            # Use subprocess directly as this is a blocking check usually done at startup
            # For async context, we might want to wrap this, but startup is fine.
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                res = result.stdout.strip().split('|')
                if len(res) >= 3:
                    self.user_id = res[0]
                    self.user_email = res[1]
                    self.org_id = res[2]
                    logger.info(f"Successfully fetched Postiz User: {self.user_id} ({self.user_email}), Org: {self.org_id}")
                    return self.user_id
            
            logger.error(f"Failed to fetch User ID. Stderr: {result.stderr}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Postiz User ID: {e}")
            return None

    def forge_token(self) -> Optional[str]:
        """Generate a valid JWT for the Postiz Internal API"""
        uid = self.get_user_id()
        if not uid:
            return None

        payload = {
            "id": uid,
            "email": getattr(self, 'user_email', 'admin@example.com'),
            "isSuperAdmin": True,
            "activated": True,
            "orgId": getattr(self, 'org_id', ''),
            "iat": int(datetime.datetime.utcnow().timestamp()),
            "exp": int((datetime.datetime.utcnow() + datetime.timedelta(hours=24)).timestamp())
        }
        
        try:
            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            return token
        except Exception as e:
            logger.error(f"Failed to forge JWT: {e}")
            return None

    async def get_auth_url(self, provider: str, callback_url: str) -> Dict:
        """Get the OAuth URL from Postiz"""
        token = self.forge_token()
        if not token:
            return {"error": "Could not generate authentication token"}

        url = f"{self.base_url}/integrations/social/{provider}"
        params = {
            "externalUrl": callback_url,
            "refresh": "", # Add empty params if needed
            "onboarding": "false"
        }
        
        headers = {
            "auth": token,
            "showorg": getattr(self, 'org_id', '')
        }
        
        session = await self.get_session()
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                logger.error(f"Postiz API Error ({resp.status}): {text}")
                return {"error": f"Postiz API returned {resp.status}", "details": text}

    async def complete_connection(self, provider: str, code: str, state: str) -> Dict:
        """Complete the connection using the code and state"""
        # Note: The completion endpoint is typically public/no-auth in Postiz 
        # (NoAuthIntegrationsController), but usually requires 'login:{state}' to be set in Redis.
        # Since we initiated the flow via the internal API (which sets Redis keys), 
        # we might just need to call the public endpoint.
        
        # Postiz Endpoint: POST /integrations/social-connect/:integration
        url = f"{self.base_url}/integrations/social-connect/{provider}"
        
        payload = {
            "code": code,
            "state": state,
            "timezone": "0", # Default
            "refresh": ""
        }
        
        headers = {
            "auth": self.forge_token() or "",
            "showorg": getattr(self, 'org_id', '')
        }
        
        session = await self.get_session()
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status < 400:
                return await resp.json()
            else:
                text = await resp.text()
                logger.error(f"Connection flow failed ({resp.status}): {text}")
                return {"error": f"Postiz API returned {resp.status}", "details": text}

    async def complete_page_connection(self, integration_id: str, state: str, page_id: str) -> Dict:
        """Complete the connection for a two-step provider (like Facebook) by selecting a page"""
        # Postiz Endpoint: POST /integrations/provider/:id/connect
        url = f"{self.base_url}/integrations/provider/{integration_id}/connect"
        
        payload = {
            "state": state,
            "page": page_id
        }
        
        headers = {
            "auth": self.forge_token() or "",
            "showorg": getattr(self, 'org_id', '')
        }
        
        session = await self.get_session()
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status < 400:
                return await resp.json()
            else:
                text = await resp.text()
                logger.error(f"Page connection failed ({resp.status}): {text}")
                return {"error": f"Postiz API returned {resp.status}", "details": text}

    async def get_supported_platforms(self) -> Dict:
        # We can implement a static list or fetch from Postiz if there's an endpoint
        # The 'internal-plugs' endpoint gives details.
        pass
