import os
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class FacebookManager:
    def __init__(self):
        self.app_id = os.getenv("FACEBOOK_APP_ID")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.api_version = "v20.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.video_url = f"https://graph-video.facebook.com/{self.api_version}"
        
        if not self.app_id or not self.app_secret:
            logging.warning("FACEBOOK_APP_ID or FACEBOOK_APP_SECRET not found in environment.")

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        scopes = [
            'pages_show_list',
            'business_management',
            'pages_manage_posts',
            'pages_manage_engagement',
            'pages_read_engagement',
            'read_insights'
        ]

        return (
            f"https://www.facebook.com/{self.api_version}/dialog/oauth"
            f"?client_id={self.app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&scope={','.join(scopes)}"
        )

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        # 1. Exchange code for short-lived user access token
        response = requests.get(
            f"{self.base_url}/oauth/access_token",
            params={
                "client_id": self.app_id,
                "redirect_uri": redirect_uri,
                "client_secret": self.app_secret,
                "code": code
            }
        )
        response.raise_for_status()
        user_token_data = response.json()
        user_access_token = user_token_data.get("access_token")

        # 2. Exchange short-lived token for long-lived user token (60 days)
        response = requests.get(
            f"{self.base_url}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": user_access_token
            }
        )
        response.raise_for_status()
        long_lived_data = response.json()
        
        return long_lived_data

    def get_pages(self, user_access_token: str) -> List[Dict]:
        response = requests.get(
            f"{self.base_url}/me/accounts",
            params={
                "access_token": user_access_token,
                "fields": "id,name,access_token,picture.type(large),username"
            }
        )
        response.raise_for_status()
        return response.json().get("data", [])

    def post_video(self, page_id: str, page_access_token: str, video_path: str, title: str, description: str) -> Dict:
        """
        Post video using multipart/form-data as requested.
        Ref: https://developers.facebook.com/docs/video-api/guides/publishing
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path}")

        url = f"{self.video_url}/{page_id}/videos"
        
        payload = {
            'description': description,
            'title': title,
            'access_token': page_access_token
        }
        
        files = {
            'source': (os.path.basename(video_path), open(video_path, 'rb'), 'video/mp4')
        }

        logging.info(f"Uploading video {video_path} to Facebook Page {page_id}...")
        response = requests.post(url, data=payload, files=files)
        
        # Close the file handle
        files['source'][1].close()
        
        if response.status_code != 200:
            logging.error(f"Facebook Video Upload Failed: {response.text}")
            response.raise_for_status()

        return response.json()

facebook_manager = FacebookManager()
