import os
import json
import uuid
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import math
from PIL import ImageEnhance
import shutil
import unicodedata
from dotenv import load_dotenv

# Load environment variables FIRST
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
import hashlib

# FastAPI
from fastapi import FastAPI, HTTPException, BackgroundTasks, Form, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn
from sqlalchemy.orm import Session

# Media processing
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import textwrap
import subprocess
import requests
from dotenv import load_dotenv
import replicate
import io
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import base64
from openai import AsyncOpenAI
import boto3
from botocore.exceptions import ClientError

# Complex script rendering
from complex_script_renderer import ComplexScriptRenderer
from font_downloader import ensure_fonts_available
from ffmpeg_downloader import ensure_ffmpeg_has_harfbuzz
from exceptions import (
    VideoPipelineError, UserInputError, ResourceMissingError, 
    FFmpegError, TimeOutError, StorageError, AssetDownloadError,
    VideoConcatenationError
)

# ========== S3 STORAGE MANAGER ==========
class S3Manager:
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.use_s3 = os.getenv("USE_S3", "false").lower() == "true"
        
        self.s3_client = None
        if self.use_s3 and self.access_key and self.secret_key:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
                logging.info(f"✓ S3 Client initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logging.error(f"Failed to initialize S3 client: {e}")
                self.use_s3 = False

    def upload_file(self, local_path: Path, s3_key: str) -> Optional[str]:
        """Upload a file to S3 and return its public URL or key reference"""
        if not self.use_s3 or not self.s3_client:
            return None
        
        try:
            # Normalize key (S3 uses forward slashes)
            s3_key = s3_key.replace("\\", "/")
            
            # Detect content type
            content_type = "application/octet-stream"
            if s3_key.endswith(".mp3"): content_type = "audio/mpeg"
            elif s3_key.endswith(".mp4"): content_type = "video/mp4"
            elif s3_key.endswith((".png", ".jpg", ".jpeg")): content_type = "image/png"
            elif s3_key.endswith(".json"): content_type = "application/json"

            self.s3_client.upload_file(
                str(local_path), 
                self.bucket_name, 
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            logging.info(f"✓ File uploaded to S3: {s3_key}")
            return f"/s3/{s3_key}" # Internal routing prefix
        except Exception as e:
            logging.error(f"S3 upload failed for {s3_key}: {e}")
            return None

    def exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3"""
        if not self.use_s3 or not self.s3_client:
            return False
        try:
            s3_key = s3_key.replace("\\", "/")
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_url(self, s3_key: str) -> str:
        """Generate a presigned URL for the S3 object (valid for 24h)"""
        if not self.use_s3 or not self.s3_client:
            return f"/storage/{s3_key}"
        
        try:
            safe_key = s3_key.replace("\\", "/")
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': safe_key
                },
                ExpiresIn=86400  # 24 hours
            )
            return url
        except Exception as e:
            safe_key = s3_key.replace("\\", "/")
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{safe_key}"

    def download_file(self, s3_key: str, local_path: Path) -> bool:
        """Download file from S3 to local disk"""
        if not self.use_s3 or not self.s3_client:
            return False
        try:
            s3_key = s3_key.replace("\\", "/")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))
            return True
        except Exception as e:
            logging.error(f"S3 download failed for {s3_key}: {e}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3"""
        if not self.use_s3 or not self.s3_client:
            return False
        try:
            s3_key = s3_key.replace("\\", "/")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logging.info(f"✓ File deleted from S3: {s3_key}")
            return True
        except Exception as e:
            logging.error(f"S3 delete failed for {s3_key}: {e}")
            return False

# New Integrations
from database import init_db, get_db, Integration, ScheduledPost
from scheduler import start_scheduler
from postiz_client import PostizClient
from postiz_client import PostizClient
from database import init_db, get_db, Integration, ScheduledPost, PostizIntegration
from postiz_auth import PostizAuthService

# Load environment variables (Moved to top)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
# ========== CONFIGURATION ==========
class Config:
    BASE_DIR = Path(__file__).parent
    STORAGE_DIR = BASE_DIR / "storage"
    
    # S3 Manager
    s3 = S3Manager()
    USE_S3 = s3.use_s3
    S3_BUCKET = s3.bucket_name
    
    # Create storage directories (always keep local for temporary processing)
    for subdir in ["audio", "visuals", "videos", "temp", "scenes", "system_defaults"]:
        (STORAGE_DIR / subdir).mkdir(parents=True, exist_ok=True)
    
    PROJECTS_FILE = STORAGE_DIR / "projects.json"
    
    # FFmpeg paths
    FFMPEG_PATH = os.path.normpath("C:/ffmpeg/bin/ffmpeg.exe")
    FFPROBE_PATH = os.path.normpath("C:/ffmpeg/bin/ffprobe.exe")
    
    # Postiz Configuration
    POSTIZ_ENABLED = os.getenv("POSTIZ_ENABLED", "true").lower() == "true"
    POSTIZ_API_KEY = os.getenv("POSTIZ_API_KEY")
    POSTIZ_BASE_URL = os.getenv("POSTIZ_BASE_URL", "http://localhost:4007")
    POSTIZ_JWT_SECRET = os.getenv("JWT_SECRET") # User must set this
    
    @classmethod
    def validate_ffmpeg_harfbuzz(cls):
        """
        CRITICAL: Validate FFmpeg has harfbuzz support for complex scripts.
        
        Automatically downloads FFmpeg with harfbuzz if needed.
        
        Raises:
            RuntimeError: If FFmpeg harfbuzz support cannot be ensured
        """
        ffmpeg_path = cls.get_ffmpeg()
        logging.info(f"Checking FFmpeg: {ffmpeg_path}")
        
        try:
            # Try to ensure harfbuzz support (downloads if needed)
            if ensure_ffmpeg_has_harfbuzz(ffmpeg_path):
                logging.info("✓ FFmpeg with harfbuzz support verified")
                return True
            else:
                # Fallback: just check that FFmpeg has drawtext filter
                result = subprocess.run(
                    [ffmpeg_path, "-filters"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                filters_output = result.stdout.lower()
                
                if "drawtext" not in filters_output:
                    raise RuntimeError(
                        "FFmpeg drawtext filter not found. "
                        "Ensure FFmpeg is properly installed."
                    )
                
                logging.warning("⚠ FFmpeg drawtext available but harfbuzz status unclear")
                logging.warning("  Complex script rendering may not work perfectly")
                return True
            
        except Exception as e:
            error_msg = (
                f"CRITICAL: FFmpeg validation failed: {e}\n"
                f"Complex script rendering requires:\n"
                f"  • FFmpeg with drawtext filter\n"
                f"  • HarfBuzz library support (--enable-libharfbuzz)\n"
                f"  • FreeType library support (--enable-libfreetype)\n"
                f"\n"
                f"Attempted to auto-download FFmpeg with harfbuzz, but failed.\n"
                f"Manual options:\n"
                f"  1. Download from: https://github.com/BtbN/FFmpeg-Builds (has harfbuzz)\n"
                f"  2. Or compile with: ./configure --enable-libharfbuzz --enable-libfreetype\n"
            )
            logging.error(error_msg)
            raise RuntimeError(error_msg)
    
    @classmethod
    def validate_ffmpeg_for_complex_scripts(cls):
        ffmpeg_path = cls.get_ffmpeg()
        logging.info(f"Validating FFmpeg for complex scripts: {ffmpeg_path}")
        
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        config = result.stdout.lower()
        
        if "--enable-libass" not in config:
            raise RuntimeError("FFmpeg missing libass (ASS subtitles required)")
            
        if "--enable-libharfbuzz" not in config:
            raise RuntimeError("FFmpeg missing harfbuzz (complex script shaping required)")
            
        if "--enable-libfreetype" not in config:
            raise RuntimeError("FFmpeg missing freetype (font rendering required)")
            
        logging.info("✓ FFmpeg validated for ASS + HarfBuzz + FreeType")
        return True



    @classmethod
    def get_ffmpeg(cls):
        return cls.FFMPEG_PATH if os.path.exists(cls.FFMPEG_PATH) else (shutil.which("ffmpeg") or "ffmpeg")
        
    @classmethod
    def get_ffprobe(cls):
        return cls.FFPROBE_PATH if os.path.exists(cls.FFPROBE_PATH) else (shutil.which("ffprobe") or "ffprobe")

# ========== MODELS ==========
class VideoCreateRequest(BaseModel):
    title: str = Field(..., max_length=100)
    script: str = Field(..., min_length=10, max_length=5000)
    language: str = "en"
    tone: str = "neutral"
    voice: str
    image_style: str
    resolution: str = "1080x1920"
    scenes_count: int = Field(8, ge=4, le=16)
    subtitle_style: str = "static"  # Options: "static", "scroll_up"
    subtitle_color: str = "white"
    subtitle_bg_visible: bool = True
    subtitle_bold: bool = False
    scenes: Optional[List[Dict[str, Any]]] = None
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        valid = ["en", "es", "fr", "de", "it", "pt", "hi", "ar", "zh", "ja", "ko", "ta"]
        if v not in valid:
            raise ValueError(f"Language must be one of {valid}")
        return v
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v):
        valid = [
            # Portrait (9:16)
            "720x1280",   # HD Portrait
            "1080x1920",  # Full HD Portrait
            "1440x2560",  # 2K Portrait
            # Landscape (16:9)
            "1280x720",   # HD Landscape
            "1920x1080",  # Full HD Landscape
            "2560x1440"   # 2K Landscape
        ]
        if v not in valid:
            raise ValueError(f"Resolution must be one of {valid}")
        return v

# ========== SCRIPT PROCESSOR ==========
class ScriptProcessor:
    @staticmethod
    def split_script(script: str, target_scenes: int = 8) -> List[Dict]:
        """Split a full script into scenes"""
        script = script.strip()
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            lines = [line.strip() for line in script.split('\n') if line.strip()]
            if lines:
                sentences = lines
            else:
                sentences = [script]
        
        # Calculate sentences per scene
        sentences_per_scene = max(1, len(sentences) // target_scenes)
        
        scenes = []
        current_scene = []
        scene_counter = 1
        
        for i, sentence in enumerate(sentences):
            current_scene.append(sentence)
            
            if (len(current_scene) >= sentences_per_scene and len(scenes) < target_scenes - 1) or i == len(sentences) - 1:
                scene_text = " ".join(current_scene)
                
                # Truncate if too long
                if len(scene_text) > 120:
                    cutoff = scene_text[:120].rfind(' ')
                    if cutoff > 80:
                        scene_text = scene_text[:cutoff] + "..."
                    else:
                        scene_text = scene_text[:117] + "..."
                
                # Estimate duration based on word count (approx 2.5 words per second)
                word_count = len(scene_text.split())
                estimated_duration = max(3, min(math.ceil(word_count / 2.5), 10))
                
                scenes.append({
                    "scene_number": scene_counter,
                    "text": scene_text,
                    "duration": estimated_duration,
                    "duration_is_auto": True,
                    "visual_prompt": f"Scene {scene_counter}: {scene_text}"  # More descriptive for Pexels
                })
                
                current_scene = []
                scene_counter += 1
        
        # Ensure we have at least target_scenes
        while len(scenes) < target_scenes and scenes:
            last_scene = scenes[-1].copy()
            last_scene["scene_number"] = len(scenes) + 1
            scenes.append(last_scene)
        
        return scenes

    @staticmethod
    async def enrich_scenes_with_voiceover(scenes: List[Dict], language: str = "en") -> List[Dict]:
        """Generate voice-overs for scenes using OpenAI/OpenRouter with fallback"""
        
        # Language mapping for better AI understanding
        lang_map = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "hi": "Hindi", "ar": "Arabic",
            "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ta": "Tamil"
        }
        lang_name = lang_map.get(language, "English")
        
        async def generate_with_client(client, model, system_prompt, user_prompt) -> Optional[List[str]]:
            try:
                logging.info(f"DEBUG: Sending request to model {model}...")
                response = await client.chat.completions.create(
                    model=model, 
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                )
                content = response.choices[0].message.content.strip()
                logging.info(f"DEBUG: AI Raw Response: {content[:100]}...")
                
                # Clean up potential markdown formatting
                if "```json" in content:
                    content = content.replace("```json", "").replace("```", "")
                elif "```" in content:
                    content = content.replace("```", "")
                
                voice_overs = json.loads(content)
                if isinstance(voice_overs, list) and len(voice_overs) == len(scenes):
                    return voice_overs
                else:
                    logging.error(f"Invalid format/count. Expected {len(scenes)}, got {len(voice_overs) if isinstance(voice_overs, list) else 'type mismatch'}")
                    return None
            except Exception as e:
                logging.error(f"Generation failed with model {model}: {e}")
                return None

        # Prepare prompts
        scenes_data = []
        for scene in scenes:
            scenes_data.append(f"Scene {scene['scene_number']} (Duration: {scene['duration']}s): {scene['text']}")
        
        scenes_block = "\n".join(scenes_data)
        
        system_prompt = f"""You are a professional video script writer. Generate a voice-over narration for each scene.

CRITICAL INSTRUCTIONS:
1. The Voice-Over MUST BE engaging and natural narration.
   - If the input text is in English, generate a creative narration in {lang_name} that is DIFFERENT from the visual description.
   - If the input text is ALREADY in {lang_name}, preserve its core meaning while ensuring it is polished and natural for speech.
   - Scene Description = What we SEE.
   - Voice Over = What we HEAR (narration).
   - Example (English input): 
     Scene: "A busy playground with kids running."
     Voice Over: "Laughter fills the air as childhood memories are made." 

2. Length must match duration (approx 2.5 words per second).
3. The Voice-Over MUST BE COMPLETELY and ONLY in {lang_name}.
4. Output ONLY a raw JSON array of strings in {lang_name}. No markdown, no code blocks."""

        user_prompt = f"""Generate {lang_name} voice-overs for these scenes. 
REMEMBER: If input is English, narration must be different and in {lang_name}. If input is {lang_name}, preserve meaning but make it natural.
MUST output ONLY the JSON array.

{scenes_block}"""

        # Try providers in order
        voice_overs = None
        
        # Try providers in order
        voice_overs = None
        
        # 1. Try OpenAI Direct (Higher reliability for these keys)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and (openai_key.startswith("sk-") or openai_key.startswith("sk-proj-")):
            try:
                logging.info(f"DEBUG: Attempting OpenAI Direct for {lang_name}...")
                client = AsyncOpenAI(api_key=openai_key)
                for model in ["gpt-4o", "gpt-3.5-turbo"]:
                    try:
                        voice_overs = await asyncio.wait_for(
                            generate_with_client(client, model, system_prompt, user_prompt),
                            timeout=30
                        )
                        if voice_overs:
                            logging.info(f"✓ Success with OpenAI Direct model: {model}")
                            break
                    except asyncio.TimeoutError:
                        logging.error(f"OpenAI Direct ({model}) request timed out")
                    except Exception as e:
                        if "insufficient_quota" in str(e):
                            logging.error(f"OpenAI Quota Exceeded: {e}")
                            break # Don't try other models if quota is gone
                        logging.error(f"OpenAI model {model} failed: {e}")
            except Exception as e:
                logging.error(f"OpenAI Direct setup failed: {e}")

        # 2. Try OpenRouter (if OpenAI failed or key missing)
        if not voice_overs:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if openrouter_key:
                # Warning: Use OpenAI keys with OpenAI, and OpenRouter keys with OpenRouter
                is_openai_key = openrouter_key.startswith("sk-proj-") or openrouter_key.startswith("sk-")
                
                try:
                    logging.info(f"DEBUG: Attempting OpenRouter for {lang_name}...")
                    client = AsyncOpenAI(
                        api_key=openrouter_key,
                        base_url="https://openrouter.ai/api/v1"
                    )
                    # Try a few reliable FREE models on OpenRouter
                    models = [
                        "google/gemini-2.0-flash-exp:free",
                        "google/gemini-pro-1.5-exp",
                        "mistralai/mistral-7b-instruct:free",
                        "openai/gpt-3.5-turbo"
                    ]
                    
                    for model in models:
                        try:
                            voice_overs = await asyncio.wait_for(
                                generate_with_client(client, model, system_prompt, user_prompt),
                                timeout=30
                            )
                            if voice_overs:
                                logging.info(f"✓ Success with OpenRouter model: {model}")
                                break
                        except asyncio.TimeoutError:
                            logging.warning(f"Timeout with OpenRouter model: {model}")
                        except Exception as e:
                            logging.error(f"OpenRouter model {model} failed: {e}")
                except Exception as e:
                    logging.error(f"OpenRouter setup failed: {e}")

        # Apply results or fallback
        if voice_overs:
            logging.info(f"DEBUG: Applying generated voice-overs for language {language} ({lang_name}).")
            for i, scene in enumerate(scenes):
                # Safety check for duplicates
                if voice_overs[i].strip().lower() == scene["text"].strip().lower():
                    logging.warning(f"Scene {i+1} voice-over identical to text. AI ignored instructions.")
                
                scene["voice_over"] = voice_overs[i]
                logging.info(f"DEBUG: Scene {i+1} Voice-Over: {voice_overs[i][:50]}...")
        else:
            logging.warning(f"ALL AI GENERATION FAILED for {lang_name}. Falling back to using scene description as voice-over.")
            for scene in scenes:
                scene["voice_over"] = scene["text"]

        # FIXED INTRO/OUTRO FOR TAMIL (As requested by user)
        if language == "ta" and len(scenes) > 0:
            logging.info("Applying fixed Tamil intro/outro phrases...")
            # First scene: Prepend fixed intro
            intro_prefix = "வணக்கம், நேயர்களே! இன்றைய ஆலயத்துளிகள் தகவல்… "
            if not scenes[0]["voice_over"].startswith(intro_prefix):
                scenes[0]["voice_over"] = intro_prefix + scenes[0]["voice_over"]
            
            # Last scene: Replace with fixed outro
            outro_text = "நன்றி.மேலும் பல ஆலயத்துளிகள் தகவல்களை அறிய எங்கள் YouTube சேனலை பாருங்கள்!"
            scenes[-1]["voice_over"] = outro_text
            scenes[-1]["text"] = outro_text

            # SYSTEM-WIDE AUDIO DEFAULTS
            # Check for permanent server-side intro/outro audio
            
            # Helper to check and apply default
            def apply_system_default(scene_index, default_type):
                meta_key = f"system_defaults/default_{default_type}.json"
                meta = None
                
                if Config.USE_S3:
                    if Config.s3.exists(meta_key):
                        # Download to temp
                        temp_meta = Config.STORAGE_DIR / "temp" / f"s3_{default_type}_meta.json"
                        if Config.s3.download_file(meta_key, temp_meta):
                            try:
                                with open(temp_meta, "r") as f:
                                    meta = json.load(f)
                            except: pass
                else:
                    local_meta = Config.STORAGE_DIR / "system_defaults" / f"default_{default_type}.json"
                    if local_meta.exists():
                        try:
                            with open(local_meta, "r") as f:
                                meta = json.load(f)
                        except: pass
                
                if meta:
                    # Check if file exists (locally or in S3)
                    exists = False
                    if Config.USE_S3:
                        # meta["path"] in S3 meta should be the key
                        exists = Config.s3.exists(meta.get("path", "").replace("\\", "/"))
                    else:
                        exists = os.path.exists(meta.get("path", ""))
                    
                    if exists:
                        pinned_text = meta.get("text", "").strip()
                        current_text = scenes[scene_index]["voice_over"].strip()
                        
                        if pinned_text == current_text:
                            # Refresh URL if using S3
                            url = meta["url"]
                            if Config.USE_S3:
                                # meta["path"] is the s3 key
                                url = Config.s3.get_url(meta["path"])
                                
                            scenes[scene_index]["audio_info"] = meta 
                            scenes[scene_index]["custom_audio_url"] = url
                            scenes[scene_index]["custom_audio_path"] = meta["path"]
                            scenes[scene_index]["duration"] = meta["duration"]
                            scenes[scene_index]["duration_is_auto"] = False
                            scenes[scene_index]["is_system_default"] = True
                            logging.info(f"✓ System Default {default_type.capitalize()} audio applied (Text matched)")
                        else:
                            logging.info(f"System Default {default_type} exists but text differs.")

            # Apply for scene 0 (intro)
            apply_system_default(0, "intro")
            
            # Apply for last scene (outro)
            apply_system_default(-1, "outro")
            
        return scenes


# ========== VIDEO GENERATOR ==========
class VideoGenerator:
    def __init__(self):
        self.projects = self._load_projects()
        self._save_projects()  # Persist any discovered legacy projects
        self.voices = self._initialize_voices()
        self.image_styles = self._initialize_image_styles()
        self.script_processor = ScriptProcessor()
        
        # CRITICAL: Validate FFmpeg has harfbuzz support
        try:
            Config.validate_ffmpeg_for_complex_scripts()
        except RuntimeError as e:
            logging.error(str(e))
            raise
        
        # CRITICAL: Initialize and validate fonts
        fonts_dir = Config.BASE_DIR / "fonts"
        try:
            ensure_fonts_available(fonts_dir)
            logging.info("✓ All essential fonts verified and available")
        except RuntimeError as e:
            logging.error(str(e))
            raise
        
        self.complex_script_renderer = ComplexScriptRenderer(fonts_dir=fonts_dir)
        logging.info("✓ Complex script renderer initialized")
        
        # Initialize AI clients
        self.replicate_token = os.getenv("REPLICATE_API_TOKEN")
        self.stability_key = os.getenv("STABILITY_API_KEY")
        
        if self.replicate_token:
            # os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
            self.replicate_client = replicate.Client(api_token=self.replicate_token)
        else:
            self.replicate_client = None
            
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        if self.elevenlabs_key:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_key)
        else:
            self.elevenlabs_client = None

        # Load projects from disk
        self.load_projects()

    def load_projects(self):
        """Load projects from JSON file"""
        self.projects_file = Config.STORAGE_DIR / "projects.json"
        try:
            if self.projects_file.exists():
                with open(self.projects_file, 'r') as f:
                    self.projects = json.load(f)
                logging.info(f"Loaded {len(self.projects)} projects from disk")
            else:
                self.projects = {}
        except Exception as e:
            logging.error(f"Failed to load projects: {e}")
            self.projects = {}

    def save_projects(self):
        """Save projects to JSON file"""
        try:
            with open(self.projects_file, 'w') as f:
                json.dump(self.projects, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save projects: {e}")
    
    def _initialize_voices(self):
        # Using popular FREE/Premade ElevenLabs voices
        return [
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel (Female)", "gender": "female", "accent": "American"},
            {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam (Male)", "gender": "male", "accent": "American"},
            {"id": "AZnzlk1XhxPqc80f0nS1", "name": "Nicole (Female)", "gender": "female", "accent": "American"},
            {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella (Female)", "gender": "female", "accent": "American"},
            {"id": "Lcf7939Ju8S8p3vKzIuK", "name": "Antoni (Male)", "gender": "male", "accent": "American"},
            {"id": "MF3mGyEYCl7XYW7Lec9M", "name": "Elli (Female)", "gender": "female", "accent": "American"},
            {"id": "ThT5KcBe7VKqW6E5mxY1", "name": "Josh (Male)", "gender": "male", "accent": "American"},
            {"id": "VR6Aewr9E3od7id8Zb6m", "name": "Arnold (Male)", "gender": "male", "accent": "American"},
            {"id": "flq6f7yk4E4f6f6f6f6f", "name": "Daniel (Male)", "gender": "male", "accent": "British"}
        ]
    
    def _initialize_image_styles(self):
        return [
            {"id": "pexels", "name": "Pexels Photo", "description": "High-quality realistic photos"}
        ]
    
    def get_voices(self):
        return self.voices
    
    def get_image_styles(self):
        return self.image_styles
    
    async def run_ffmpeg_safe(self, cmd: list, timeout: int = 60, context: str = "operation") -> str:
        """
        Executes FFmpeg with safety rails. 
        1. Captures stderr
        2. Enforces timeout
        3. Checks output file existence
        4. Raises typed exceptions (No swallowing errors!)
        """
        try:
            logging.info(f"Starting FFmpeg: {context}")
            # Use asyncio.to_thread to avoid blocking the event loop
            result = await asyncio.to_thread(
                subprocess.run, 
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                encoding='utf-8', 
                errors='ignore'
            )
            
            if result.returncode != 0:
                # Parse stderr for common errors
                error_msg = f"FFmpeg exited with code {result.returncode}"
                details = result.stderr[-1000:] # Last 1000 chars
                
                if "No such file or directory" in details:
                    raise ResourceMissingError("Input file missing during rendering", details)
                if "Permission denied" in details:
                    raise StorageError("Permission denied writing output", details)
                    
                raise FFmpegError(error_msg, details)
                
            return result.stderr # FFmpeg usually logs stats to stderr, which is fine
            
        except subprocess.TimeoutExpired:
            raise TimeOutError(f"FFmpeg timed out after {timeout}s", f"Context: {context}")
            
        except Exception as e:
            if isinstance(e, VideoPipelineError): raise e
            raise VideoPipelineError(f"Unexpected error: {str(e)}", "UNKNOWN_ERROR", str(e))
    
    def _parse_resolution(self, resolution: str) -> tuple:
        """Parse resolution string to (width, height) tuple"""
        try:
            width, height = resolution.split('x')
            return int(width), int(height)
        except:
            # Default to portrait Full HD if parsing fails
            return 1080, 1920
    
    async def generate_audio(self, text: str, language: str = "en", voice_id: str = None) -> Dict:
        """Generate audio using ElevenLabs TTS API"""
        try:
            if not self.elevenlabs_client:
                logging.error("ElevenLabs client not initialized. Please provide ELEVENLABS_API_KEY in .env.")
                return {"url": "", "duration": 5.0, "path": ""}

            # Find the correct voice id or default to Rachel
            voice = voice_id if voice_id else "21m00Tcm4TlvDq8ikWAM"
            
            # Ensure storage directory exists
            audio_dir = Config.STORAGE_DIR / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            # CONTENT-BASED CACHING: Prevent redundant ElevenLabs API calls
            # MD5 hash of (text + voice) ensures uniqueness per narration
            cache_key = f"{text}_{voice}_eleven_multilingual_v2"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            filename = f"cached_{cache_hash}.mp3"
            audio_file = Config.STORAGE_DIR / "audio" / filename
            s3_key = f"audio/{filename}"
            
            # S3 CACHE CHECK
            if Config.USE_S3 and Config.s3.exists(s3_key):
                logging.info(f"✓ S3 AUDIO CACHE HIT: {s3_key}")
                if not audio_file.exists():
                    Config.s3.download_file(s3_key, audio_file)
                
                if audio_file.exists():
                    duration = self._get_audio_duration(audio_file)
                    return {
                        "url": Config.s3.get_url(s3_key),
                        "duration": duration,
                        "path": str(audio_file),
                        "s3_key": s3_key,
                        "generation_text": text,
                        "voice_id": voice,
                        "cached": True
                    }

            # LOCAL CACHE CHECK
            if audio_file.exists():
                logging.info(f"✓ LOCAL AUDIO CACHE HIT: {filename}")
                duration = self._get_audio_duration(audio_file)
                
                # Upload to S3 if missing there but exists locally
                if Config.USE_S3:
                    Config.s3.upload_file(audio_file, s3_key)
                
                return {
                    "url": Config.s3.get_url(s3_key) if Config.USE_S3 else f"/storage/audio/{filename}",
                    "duration": duration,
                    "path": str(audio_file),
                    "s3_key": s3_key if Config.USE_S3 else None,
                    "generation_text": text,
                    "voice_id": voice,
                    "cached": True
                }

            logging.info(f"Generating NEW ElevenLabs audio for voice {voice}...")
            
            # Call ElevenLabs API
            def _generate():
                return self.elevenlabs_client.text_to_speech.convert(
                    text=text,
                    voice_id=voice,
                    model_id="eleven_multilingual_v2"
                )

            audio_stream = await asyncio.get_event_loop().run_in_executor(None, _generate)
            
            # Save the result
            save(audio_stream, str(audio_file))
            
            if audio_file.exists():
                duration = self._get_audio_duration(audio_file)
                
                # Upload to S3
                if Config.USE_S3:
                    Config.s3.upload_file(audio_file, s3_key)

                return {
                    "url": Config.s3.get_url(s3_key) if Config.USE_S3 else f"/storage/audio/{filename}",
                    "duration": duration,
                    "path": str(audio_file),
                    "s3_key": s3_key if Config.USE_S3 else None,
                    "generation_text": text,
                    "voice_id": voice,
                    "cached": False
                }
            
            return {"url": "", "duration": 5.0, "path": ""}

        except Exception as e:
            error_msg = str(e).lower()
            if any(k in error_msg for k in ["quota", "credit", "insufficient"]):
                logging.error(f"CRITICAL: ElevenLabs Quota Exceeded: {e}")
                return {"url": "", "duration": 5.0, "path": "", "error_code": "QUOTA_EXCEEDED"}
            
            logging.error(f"ElevenLabs audio generation error: {e}")
            return {"url": "", "duration": 5.0, "path": ""}
    
    async def _create_silent_audio(self, duration: float) -> Dict:
        """Create a silent audio file for the specified duration"""
        try:
            audio_id = f"silent_{uuid.uuid4().hex[:8]}"
            audio_file = Config.STORAGE_DIR / "temp" / f"{audio_id}.mp3"
            audio_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use ffmpeg to generate silence
            cmd = [
                Config.get_ffmpeg(),
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(duration),
                "-ar", "44100",
                "-ac", "2",
                "-acodec", "libmp3lame",
                "-y",
                str(audio_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and audio_file.exists():
                return {
                    "url": f"/storage/temp/{audio_id}.mp3",
                    "duration": duration,
                    "path": str(audio_file)
                }
            
            return {"url": "", "duration": duration, "path": ""}
        except Exception as e:
            logging.error(f"Silent audio creation failed: {e}")
            return {"url": "", "duration": duration, "path": ""}

    def _load_projects(self) -> Dict[str, Any]:
        """Load projects from JSON file and discover orphan videos"""
        projects = {}
        if Config.PROJECTS_FILE.exists():
            try:
                with open(Config.PROJECTS_FILE, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load projects: {e}")
        
        # Discover orphan videos that aren't in the JSON
        self._discover_legacy_videos(projects)
        return projects

    def _discover_legacy_videos(self, projects: Dict[str, Any]):
        """Scan storage/videos and add orphans to projects as 'legacy' entries"""
        videos_dir = Config.STORAGE_DIR / "videos"
        if not videos_dir.exists():
            return

        # Get existing video URLs from projects
        known_urls = {p.get("video_url") for p in projects.values() if p.get("video_url")}

        for video_file in videos_dir.glob("*.mp4"):
            video_url = f"/storage/videos/{video_file.name}"
            if video_url not in known_urls:
                # This is a legacy/orphan video
                project_id = f"legacy_{video_file.stem}"
                # Use file modification time as creation time
                mtime = datetime.fromtimestamp(video_file.stat().st_mtime).isoformat()
                
                projects[project_id] = {
                    "id": project_id,
                    "title": f"Restored: {video_file.name}",
                    "status": "completed",
                    "progress": 100,
                    "video_url": video_url,
                    "created_at": mtime,
                    "is_legacy": True
                }
                logging.info(f"Discovered legacy video: {video_file.name}")

    def _save_projects(self):
        """Save projects to JSON file"""
        try:
            logging.info(f"Attempting to save {len(self.projects)} projects to {Config.PROJECTS_FILE}")
            # Ensure directory exists
            Config.PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Use a temporary file for atomic write
            temp_file = Config.PROJECTS_FILE.with_suffix(".tmp")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)
            
            # Rename temp file to actual file
            if os.path.exists(Config.PROJECTS_FILE):
                os.replace(temp_file, Config.PROJECTS_FILE)
            else:
                os.rename(temp_file, Config.PROJECTS_FILE)
                
            logging.info(f"✓ Projects saved successfully to {Config.PROJECTS_FILE}")
        except Exception as e:
            logging.error(f"CRITICAL: Failed to save projects to {Config.PROJECTS_FILE}: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                Config.get_ffprobe(),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            return 5.0  # Default duration
        except:
            # Estimate duration: 0.15 seconds per word
            words = len(str(audio_path).split()) if isinstance(audio_path, str) else 0
            return max(3.0, min(words * 0.15, 10.0))
    
    def _format_visual_response(self, visual_file: Path, style: str, visual_id: str) -> Dict:
        """Helper to format visual response and upload to S3 if needed"""
        s3_key = f"visuals/{visual_file.name}"
        if Config.USE_S3:
            Config.s3.upload_file(visual_file, s3_key)
            return {
                "url": Config.s3.get_url(s3_key),
                "path": str(visual_file),
                "s3_key": s3_key,
                "style": style
            }
        return {
            "url": f"/storage/visuals/{visual_id}.png",
            "path": str(visual_file),
            "style": style
        }

    async def generate_visual(self, prompt: str, style: str, scene_number: int, resolution: str = "1080x1920", custom_image_path: Optional[str] = None) -> Dict:
        """Generate visual with AI providers or fallback to PIL"""
        try:
            visual_id = f"visual_{uuid.uuid4().hex[:8]}"
            visual_file = Config.STORAGE_DIR / "visuals" / f"{visual_id}.png"
            visual_file.parent.mkdir(parents=True, exist_ok=True)
            
            # If custom image path is provided, use it
            if custom_image_path and os.path.exists(custom_image_path):
                logging.info(f"Using custom image for scene {scene_number}: {custom_image_path}")
                # Copy to visuals directory with a new name to avoid conflicts and ensure it's in the right place
                shutil.copy2(custom_image_path, visual_file)
                return self._format_visual_response(visual_file, "custom", visual_id)

            # Parse resolution for dimensions
            width, height = self._parse_resolution(resolution)
            
            # 0. Try Pexels First if explicitly selected as style
            if style == "pexels" and self.pexels_key:
                try:
                    logging.info(f"Pexels style selected, attempting Pexels search for scene {scene_number}...")
                    image_url = await self._generate_with_pexels(prompt, style)
                    if image_url:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            with open(visual_file, "wb") as f:
                                f.write(response.content)
                            logging.info(f"✓ Found visual via Pexels (Style Priority): {visual_file}")
                            return self._format_visual_response(visual_file, style, visual_id)
                except Exception as pe:
                    logging.warning(f"Pexels search failed (Style Priority): {pe}")

            # 1. Try Replicate (SDXL or Flux)
            if self.replicate_token:
                try:
                    logging.info(f"Attempting Replicate generation for scene {scene_number}...")
                    image_url = await self._generate_with_replicate(prompt, style)
                    if image_url:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            with open(visual_file, "wb") as f:
                                f.write(response.content)
                            logging.info(f"✓ Generated visual via Replicate: {visual_file}")
                            return self._format_visual_response(visual_file, style, visual_id)
                except Exception as re:
                    logging.warning(f"Replicate generation failed: {re}")

            # 2. Try Stability AI
            if self.stability_api:
                try:
                    logging.info(f"Attempting Stability generation for scene {scene_number}...")
                    image_data = await self._generate_with_stability(prompt, style)
                    if image_data:
                        with open(visual_file, "wb") as f:
                            f.write(image_data)
                        logging.info(f"✓ Generated visual via Stability: {visual_file}")
                        return self._format_visual_response(visual_file, style, visual_id)
                except Exception as se:
                    logging.warning(f"Stability generation failed: {se}")

            # 3. Try HuggingFace
            if self.hf_token:
                try:
                    logging.info(f"Attempting HuggingFace generation for scene {scene_number}...")
                    image_data = await self._generate_with_huggingface(prompt, style)
                    if image_data and len(image_data) > 5000:
                        with open(visual_file, "wb") as f:
                            f.write(image_data)
                        logging.info(f"✓ Generated visual via HuggingFace: {visual_file}")
                        return self._format_visual_response(visual_file, style, visual_id)
                except Exception as he:
                    logging.warning(f"HuggingFace generation failed: {he}")

            # 5. Try Pexels (Search for realistic images)
            if self.pexels_key:
                try:
                    logging.info(f"Attempting Pexels search for scene {scene_number}...")
                    image_url = await self._generate_with_pexels(prompt, style)
                    if image_url:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            with open(visual_file, "wb") as f:
                                f.write(response.content)
                            logging.info(f"✓ Found visual via Pexels: {visual_file}")
                            return self._format_visual_response(visual_file, style, visual_id)
                except Exception as pe:
                    logging.warning(f"Pexels search failed: {pe}")

            # 6. Last Fallback: PIL Gradient
            logging.info(f"Falling back to PIL generation for scene {scene_number}")
            img = self._create_base_image(style, width, height)
            img = self._add_scene_number_to_image(img, scene_number, style)
            img.save(str(visual_file), "PNG", quality=95)
            
            return self._format_visual_response(visual_file, style, visual_id)
            
        except Exception as e:
            logging.error(f"Visual generation failed completely: {e}")
            return self._create_fallback_image(scene_number, style, resolution)

    async def _generate_with_replicate(self, prompt: str, style: str) -> Optional[str]:
        """Generate image using Replicate's Flux model"""
        try:
            if not self.replicate_client:
                return None
                
            full_prompt = f"{prompt}, {style} style, high quality, 4k, cinematic"
            if style == "anime":
                full_prompt = f"anime style, {prompt}, vibrant colors, high resolution"
            elif style == "pixar_art":
                full_prompt = f"pixar animated movie style, 3d render, {prompt}, cute, high detail"
            
            print(f"DEBUG: Using Replicate model: stability-ai/sdxl")
            output = self.replicate_client.run(
                "stability-ai/sdxl:7762fd0e20c1440f994645da621dc7fb0217595f391809084897f7fa043588da",
                input={
                    "prompt": full_prompt,
                    "negative_prompt": "low quality, blurry, distorted, text, watermark",
                    "width": 1024,
                    "height": 1024,
                    "num_outputs": 1
                }
            )
            if output and isinstance(output, list) and len(output) > 0:
                return output[0]
            return None
        except Exception as e:
            logging.error(f"Replicate API error: {e}")
            return None

    async def _generate_with_stability(self, prompt: str, style: str) -> Optional[bytes]:
        """Generate image using Stability AI's REST API"""
        try:
            if not self.stability_key:
                return None
                
            full_prompt = f"{prompt}, {style} style, high quality, 4k"
            
            engine_id = "stable-diffusion-xl-1024-v1-0"
            api_host = "https://api.stability.ai"
            
            response = requests.post(
                f"{api_host}/v1/generation/{engine_id}/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.stability_key}"
                },
                json={
                    "text_prompts": [
                        {
                            "text": full_prompt,
                            "weight": 1
                        },
                        {
                            "text": "blurry, low quality, distorted, text, watermark",
                            "weight": -1
                        }
                    ],
                    "cfg_scale": 7,
                    "height": 1024,
                    "width": 1024,
                    "samples": 1,
                    "steps": 30,
                },
            )

            if response.status_code != 200:
                logging.error(f"Stability API error: {response.text}")
                return None

            data = response.json()
            for i, image in enumerate(data["artifacts"]):
                if image["finishReason"] == "CONTENT_FILTERED":
                    logging.warning("Stability AI filtered the request")
                    return None
                return base64.b64decode(image["base64"])
            
            return None
        except Exception as e:
            logging.error(f"Stability API error: {e}")
            return None

    async def _generate_with_huggingface(self, prompt: str, style: str) -> Optional[bytes]:
        """Generate image using Hugging Face's Inference API"""
        try:
            if not self.hf_token:
                return None
            
            # Using Stable Diffusion v1.5 (Non-gated)
            api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            
            full_prompt = f"{prompt}, {style} style, high quality, masterpiece, cinematic"
            
            response = requests.post(
                api_url, 
                headers=headers, 
                json={
                    "inputs": full_prompt,
                    "parameters": {"negative_prompt": "blurry, low quality, distorted, text, watermark"}
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                logging.info("HuggingFace model is loading...")
                return None
            else:
                logging.error(f"HuggingFace API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logging.error(f"HuggingFace API error: {e}")
            return None

    async def _generate_with_openrouter(self, prompt: str, style: str) -> Optional[str]:
        """Generate image using OpenRouter (as a proxy if available) or other providers"""
        # Note: OpenRouter primarily handles LLMs. 
        # But we can try to use it for image generation if the key allows.
        # However, it's safer to try a direct DALL-E or similar if we had a key.
        # Since we don't, we'll try to use OpenRouter to generate a better prompt as a fallback
        return None

    async def _generate_with_pexels(self, prompt: str, style: str) -> Optional[str]:
        """Search for a photo on Pexels based on the prompt"""
        try:
            if not self.pexels_key:
                return None
            
            # Clean prompt for better search results
            search_query = prompt
            if "Visual for scene" in search_query or "Scene " in search_query:
                # Extract the actual descriptive part
                parts = search_query.split(":", 1)
                if len(parts) > 1:
                    search_query = parts[1].strip()
            
            # Simple keyword extraction if prompt is too long or complex
            # For now, just use the first 150 chars for more specificity
            search_query = search_query[:150]
            
            url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=1"
            headers = {"Authorization": self.pexels_key}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    # Prefer large or original size
                    return data["photos"][0]["src"].get("large2x") or data["photos"][0]["src"].get("original")
            
            return None
        except Exception as e:
            logging.error(f"Pexels API error: {e}")
            return None
    
    def _create_fallback_image(self, scene_number: int, style: str, resolution: str = "1080x1920") -> Dict:
        """Create a fallback image when generation fails"""
        try:
            visual_id = f"fallback_{uuid.uuid4().hex[:8]}"
            visual_file = Config.STORAGE_DIR / "visuals" / f"{visual_id}.png"
            
            width, height = self._parse_resolution(resolution)
            img = Image.new('RGB', (width, height), color='#667eea')
            draw = ImageDraw.Draw(img)
            
            # Add scene number
            try:
                font = ImageFont.truetype("arial.ttf", 100) if os.name == 'nt' else ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            draw.text((width//2 - 100, height//2 - 50), f"Scene {scene_number}", font=font, fill='white')
            draw.text((width//2 - 200, height//2 + 50), style.capitalize(), font=font, fill='white')
            
            img.save(str(visual_file), "PNG")
            
            return {
                "url": f"/storage/visuals/{visual_id}.png",
                "path": str(visual_file),
                "style": style
            }
        except:
            return {"url": "", "path": "", "style": style}
    
    def _create_base_image(self, style: str, width: int, height: int) -> Image.Image:
        """Create base image with style-specific background"""
        import random
        
        # Default gradient background
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # Create gradient
        for i in range(height):
            if style == "anime":
                r = int(255 * (1 - i/(height*1.5)))
                g = int(200 * (1 - i/(height*2)))
                b = int(225 * (1 - i/(height*2.5)))
            elif style == "pixar_art":
                r = int(135 + (50 * i / height))
                g = int(206 + (30 * i / height))
                b = int(235 + (20 * i / height))
            elif style == "comic":
                r = int(255 - (100 * i / height))
                g = int(215 - (100 * i / height))
                b = int(0 + (50 * i / height))
            elif style == "lego":
                r = int(255 - (150 * i / height))
                g = int(107 - (50 * i / height))
                b = int(107 - (30 * i / height))
            elif style == "cinematic":
                brightness = int(10 + (100 * i / height))
                r = g = b = brightness
            else:  # default
                r = int(26 + (100 * i / height))
                g = int(26 + (150 * i / height))
                b = int(46 + (100 * i / height))
            
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        # Add style-specific decorations
        if style == "anime":
            for _ in range(15):
                x = random.randint(50, width - 50)
                y = random.randint(50, height - 50)
                size = random.randint(20, 40)
                color = (255, random.randint(180, 220), random.randint(200, 240), 128)
                draw.ellipse([x-size, y-size, x+size, y+size], 
                           fill=color, outline=None)
        
        elif style == "pixar_art":
            for _ in range(3):
                x = random.randint(100, width - 200)
                y = random.randint(50, 200)
                cloud_w = random.randint(150, 250)
                draw.ellipse([x, y, x+cloud_w, y+80], 
                           fill=(255, 255, 255, 180), outline=None)
        
        elif style == "comic":
            # Add comic dots
            dot_size = 3
            spacing = 10
            for y in range(0, height, spacing):
                for x in range(0, width, spacing):
                    if (x + y) % 20 == 0:
                        draw.ellipse([x-dot_size, y-dot_size, x+dot_size, y+dot_size], 
                                   fill='black')
        
        return img
    
    def _add_scene_number_to_image(self, img: Image.Image, scene_number: int, style: str) -> Image.Image:
        """Add scene number to the image"""
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to load a font
            if os.name == 'nt':  # Windows
                font_path = "C:/Windows/Fonts/arial.ttf"
            else:  # Linux/Mac
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            
            try:
                font = ImageFont.truetype(font_path, 80)
            except:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        text = f"Scene {scene_number}"
        text_color = 'white' if style in ["cinematic", "default"] else 'black'
        
        # Get text bounding box
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width, text_height = 200, 100
        
        x = (img.width - text_width) // 2
        y = 100
        
        draw.text((x, y), text, font=font, fill=text_color)
        
        return img
    
    async def create_scene_video(self, scene: Dict, audio_info: Dict, visual_info: Dict, style: str, 
                                resolution: str = "1080x1920", language: str = "en",
                                subtitle_style: str = "static") -> Optional[str]:
        """Create a single scene video with audio and text overlay"""
        try:
            # Create scenes directory if it doesn't exist
            scenes_dir = Config.STORAGE_DIR / "scenes"
            scenes_dir.mkdir(parents=True, exist_ok=True)
            
            scene_file = scenes_dir / f"scene_{scene['scene_number']}_{uuid.uuid4().hex[:6]}.mp4"
            
            # Priority: Use PIL-based text overlay (Method 2) first, as it's more robust on Windows
            logging.info(f"Creating scene video for scene {scene['scene_number']}...")
            # Subtitle should be the visual text (Visual Prompt).
            subtitle_text = scene.get('text', scene.get('voice_over', ''))
            
            # Determine final duration
            # Priority:
            # 1. Manual duration (if duration_is_auto is False/missing but value changed)
            # 2. Actual audio duration (the safest for narration)
            manual_duration = scene.get("duration")
            is_auto = scene.get("duration_is_auto", False)
            
            # If it's auto-estimated, we prefer the actual audio duration to avoid cuts
            # If the user changed it manually, we respect their choice
            final_duration = audio_info["duration"] if is_auto else manual_duration
            
            logging.info(f"Duration logic: is_auto={is_auto}, manual={manual_duration}, audio={audio_info['duration']} -> final={final_duration}")

            scene_path = await self._create_scene_with_simple_text(
                visual_info["path"], 
                audio_info["path"], 
                scene_file, 
                final_duration,
                subtitle_text if not scene.get("show_image_only", False) else "",
                resolution,
                language,
                subtitle_style=subtitle_style,
                subtitle_position=scene.get("subtitle_position", "bottom"),
                subtitle_size=scene.get("subtitle_size", 60),
                subtitle_color=scene.get("subtitle_color", "white"),
                subtitle_bg_visible=scene.get("subtitle_bg_visible", True),
                subtitle_bold=scene.get("subtitle_bold", False),
                rotation=scene.get("rotation", 0),
                line_styles=scene.get("line_styles", [])
            )
            
            if scene_path:
                return scene_path
                
            # Fallback 1: Try direct FFmpeg drawtext (Method 1)
            logging.warning("PIL overlay failed or not returned path, trying FFmpeg drawtext...")
            
            # Prepare text for FFmpeg - escape special characters
            text_for_ffmpeg = subtitle_text.replace("'", "'\\\\\\''").replace(':', '\\:').replace(',', '\\,')
            
            if len(text_for_ffmpeg) > 100:
                text_for_ffmpeg = text_for_ffmpeg[:97] + "..."

            try:
                cmd = [
                    Config.get_ffmpeg(),
                    "-loop", "1",
                    "-i", visual_info["path"],
                    "-i", audio_info["path"],
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-t", str(audio_info["duration"]),
                    "-vf", f"scale={resolution.replace('x', ':')}:force_original_aspect_ratio=decrease,pad={resolution.replace('x', ':')}:(ow-iw)/2:(oh-ih)/2:color=black,"
                           f"drawtext=text='{text_for_ffmpeg}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=h-text_h-200",
                    "-shortest",
                    "-y",
                    str(scene_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and scene_file.exists():
                    return str(scene_file)
            except Exception as e:
                logging.error(f"FFmpeg drawtext failed: {e}")

            # Fallback 2: Simple video without text
            return await self._create_simple_scene_video(
                visual_info["path"], 
                audio_info["path"], 
                scene_file, 
                audio_info["duration"],
                resolution
            )
            
        except Exception as e:
            logging.error(f"Scene video creation failed: {e}")
            return None
            
    async def _create_scene_with_simple_text(self, image_path: str, audio_path: str, 
                                           output_path: Path, duration: float, 
                                           text: str, resolution: str = "1080x1920", language: str = "en",
                                           subtitle_style: str = "static", 
                                           subtitle_position: str = "bottom",
                                           subtitle_size: int = 60,
                                           subtitle_color: str = "white",
                                           subtitle_bg_visible: bool = True,
                                           subtitle_bold: bool = False,
                                           rotation: int = 0,
                                           line_styles: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Create scene video with proper complex script handling
        
        CRITICAL PIPELINE CHANGE:
        - Simple Scripts (English): Use optimized PIL fallback (Fast)
        - Complex Scripts (Tamil/Hindi): Use LIBASS (.ass) pipeline (Correct)
        """
        try:
            # STEP 1: Normalize Unicode immediately after extraction
            text = unicodedata.normalize("NFC", text)
            logging.info(f"✓ Unicode normalized for language '{language}'")
            
            # STEP 2: Check standard pipelines
            renderer = self.complex_script_renderer
            
            if language not in renderer.COMPLEX_SCRIPTS and subtitle_style == "static":
                # FAST PATH: Use PIL for simple scripts (English, etc.) without animation
                return await self._create_scene_with_pil_fallback(
                    image_path, audio_path, output_path, duration, text, resolution, language,
                    subtitle_position=subtitle_position,
                    subtitle_size=subtitle_size,
                    subtitle_color=subtitle_color,
                    subtitle_bg_visible=subtitle_bg_visible,
                    subtitle_bold=subtitle_bold,
                    rotation=rotation,
                    line_styles=line_styles
                )
            
            # === COMPLEX SCRIPT PIPELINE (ASS/LIBASS) ===
            logging.info(f"Entering Complex Script Pipeline (LIBASS) for {language}")
            
            return await self._create_scene_with_complex_script(
                image_path, audio_path, output_path, duration, text, 
                resolution, language, subtitle_style, subtitle_position, 
                subtitle_size, subtitle_color, subtitle_bg_visible, subtitle_bold, rotation,
                line_styles=line_styles
            )
        except Exception as e:
            logging.error(f"Error in simple text creation: {e}")
            return None

    async def _create_scene_with_complex_script(self, image_path: str, audio_path: str, 
                                              output_path: Path, duration: float, 
                                              text: str, resolution: str = "1080x1920", language: str = "en",
                                              subtitle_style: str = "static",
                                              subtitle_position: str = "bottom",
                                              subtitle_size: int = 60,
                                              subtitle_color: str = "white",
                                              subtitle_bg_visible: bool = True,
                                              subtitle_bold: bool = False,
                                              rotation: int = 0,
                                              line_styles: Optional[List[Dict[str, Any]]] = None) -> str:
        """Create scene video using LIBASS/ASS pipeline for complex scripts"""
        try:
            renderer = self.complex_script_renderer
            # 1. Find Font
            font_path = renderer.find_font(language)
            if not font_path:
                msg = f"CRITICAL: No font found for {language}. Cannot generate subtitles."
                logging.error(msg)
                raise RuntimeError(msg)
            
            # 2. Wrap Text
            max_width_lines = 3000  # Set high to let Libass handle accurate wrapping via margins
            font_size = subtitle_size  # Use customized font size
            
            # --- DYNAMIC POSITIONING ---
            try:
                # Calculate Layout: Image Center-Aligned
                # Goal: Subtitles at Bottom of Image (inside)
                with Image.open(image_path) as img:
                    img_w, img_h = img.size
                
                vid_w, vid_h = self._parse_resolution(resolution)
                
                # Calculate new dimensions after scaling
                ratio = min(vid_w / img_w, vid_h / img_h)
                scaled_h = int(img_h * ratio)
                
                # Calculate MarginV (Distance from Video Bottom)
                # Image is Vertically Centered.
                # Top Black Bar = Bottom Black Bar = (VidH - ScaledH) / 2
                # Image Bottom = VidH - Bottom Black Bar
                # Distance from Video Bottom to Image Bottom = Bottom Black Bar
                # We want text INSIDE image, so add inner margin to that.
                
                bottom_bar_height = (vid_h - scaled_h) // 2
                inner_margin = 80  # Padding inside the image
                
                if subtitle_position == 'center':
                    margin_v = vid_h // 2
                else: # bottom
                    margin_v = bottom_bar_height + inner_margin
                
                logging.info(f"Layout Calc: VidH={vid_h}, ImgH={scaled_h}, BottomBar={bottom_bar_height}, MarginV={margin_v}")
            except Exception as e:
                logging.error(f"Error calculating subtitle position: {e}")
                margin_v = 100 # Fallback
            
            lines = renderer.wrap_text_at_word_boundaries(
                text, max_width_lines, font_path, font_size, language
            )
            wrapped_text = "\n".join(lines)
            
            # 3. Generate ASS File
            ass_file_path = Config.STORAGE_DIR / "temp" / f"sub_{uuid.uuid4().hex}.ass"
            ass_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            renderer.generate_ass_file(
                text,
                ass_file_path,
                font_path,
                font_size=font_size,
                duration=duration,
                resolution=resolution,
                language=language,
                margin_v=margin_v,
                style=subtitle_position if subtitle_style == "static" else subtitle_style,
                color=subtitle_color,
                bg_visible=subtitle_bg_visible,
                bold=subtitle_bold,
                line_styles=line_styles
            )
            
            # 4. Generate Clean Video (Image + Audio) - Intermediate
            temp_video = Config.STORAGE_DIR / "temp" / f"raw_{uuid.uuid4().hex}.mp4"
            width, height = resolution.split('x')
            
            # Create base video first
            cmd_base = [
                Config.get_ffmpeg(),
                "-loop", "1",
                "-r", "30",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-r", "30",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-pix_fmt", "yuv420p",
                "-vf", f"rotate={rotation}*PI/180:ow='max(iw,ih)':oh='max(iw,ih)',"
                       f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
                "-af", f"atrim=0:{duration},apad=whole_dur={duration}",
                "-t", str(duration),
                "-shortest",
                "-y",
                str(temp_video)
            ]
            subprocess.run(cmd_base, check=True, capture_output=True)
            
            # 5. Burn ASS Subtitles (Video + ASS -> Final Video)
            # Use forward slashes for filter paths to be safe on Windows
            ass_path_filter = str(ass_file_path).replace('\\', '/').replace(':', '\\:')
            # We must specify fontsdir to ensure libass finds the font if it's local
            fonts_dir_filter = str(Config.BASE_DIR / "fonts").replace('\\', '/').replace(':', '\\:')
            
            cmd_burn = [
                Config.get_ffmpeg(),
                "-i", str(temp_video),
                "-vf", f"ass='{ass_path_filter}':fontsdir='{fonts_dir_filter}'",
                "-c:a", "copy",
                "-y",
                str(output_path)
            ]
            
            await self.run_ffmpeg_safe(cmd_burn, timeout=60, context=f"Burning subtitles for {language}")
            
            # Cleanup
            if ass_file_path.exists(): ass_file_path.unlink()
            if temp_video.exists(): temp_video.unlink()
            
            if output_path.exists():
                logging.info(f"✓ Scene video with ASS subtitles created: {output_path}")
                return str(output_path)
            else:
                raise FFmpegError("Scene video output not found after burning", str(output_path))
                
        except Exception as e:
            logging.error(f"Complex script rendering failed: {e}")
            # Re-raise nicely
            if isinstance(e, VideoPipelineError): raise e
            raise FFmpegError(f"Rendering failed for {language}: {e}")
    
    async def _create_scene_with_pil_fallback(self, image_path: str, audio_path: str, 
                                            output_path: Path, duration: float, 
                                            text: str, resolution: str = "1080x1920", language: str = "en",
                                            subtitle_position: str = "bottom",
                                            subtitle_size: int = 60,
                                            subtitle_color: str = "white",
                                            subtitle_bg_visible: bool = True,
                                            subtitle_bold: bool = False,
                                            rotation: int = 0,
                                            line_styles: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Fallback PIL-based text rendering for simple scripts ONLY
        
        WARNING: Complex scripts (Tamil, Hindi, etc.) MUST NOT use PIL rendering.
        PIL cannot perform proper glyph shaping and will produce broken output.
        This method should only be called for simple scripts (English, etc.)
        """
        # HARD ASSERTION: Reject complex scripts
        self.complex_script_renderer.assert_not_pil_for_complex_script(
            language, 
            f"PIL fallback method called for language '{language}'. Complex scripts require FFmpeg with harfbuzz."
        )
        
        try:
            temp_image = Config.STORAGE_DIR / "temp" / f"temp_text_{uuid.uuid4().hex[:8]}.png"
            temp_image.parent.mkdir(parents=True, exist_ok=True)
            
            # Ensure Unicode is normalized
            text = unicodedata.normalize("NFC", text)
            
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            draw = ImageDraw.Draw(img)
            
            # Get font for language
            renderer = self.complex_script_renderer
            font_path = renderer.find_font(language)
            
            if not font_path:
                font_path = "C:/Windows/Fonts/arial.ttf" if os.name == 'nt' else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            
            # Dynamic fitting loop
            max_width = img.width - 120
            max_height = img.height * 0.4
            font_size = 60
            
            fitting = True
            lines = []
            
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
                font_size = 20
            
            # Wrap at word boundaries
            while fitting and font_size > 12:
                lines = []
                words = text.split()
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    w = bbox[2] - bbox[0]
                    if w <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                        else:
                            lines.append(word)
                            current_line = []
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Check height
                temp_bbox = draw.textbbox((0, 0), "Ayg", font=font)
                line_height_from_font = (temp_bbox[3] - temp_bbox[1]) + 15
                total_height = len(lines) * line_height_from_font
                
                if total_height > max_height:
                    font_size -= 4
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                    except:
                        fitting = False
                else:
                    fitting = False
            
            # === STYLING & RENDERING ===
            color_map = {
                'white': (255, 255, 255), 'yellow': (255, 255, 0), 'cyan': (0, 255, 255),
                'green': (0, 255, 0), 'red': (255, 0, 0), 'orange': (255, 165, 0),
                'blue': (0, 0, 255), 'pink': (255, 192, 203), 'purple': (128, 0, 128),
                'black': (0, 0, 0)
            }

            def get_font_for_line(size, is_bold):
                f_path = font_path
                if is_bold:
                    if os.name == 'nt':
                        font_path_bold = "C:/Windows/Fonts/arialbd.ttf"
                        if os.path.exists(font_path_bold): f_path = font_path_bold
                    else:
                        font_path_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                        if os.path.exists(font_path_bold): f_path = font_path_bold
                try:
                    return ImageFont.truetype(f_path, size)
                except:
                    return ImageFont.load_default()

            if line_styles:
                lines = text.split('\n')
            
            prepared_lines = []
            total_height = 0
            padding = 15
            l_styles = line_styles or []

            for i, line_text in enumerate(lines):
                line_text = line_text.strip()
                if not line_text:
                    total_height += int(subtitle_size * 1.2)
                    prepared_lines.append(None)
                    continue
                
                l_style = l_styles[i] if i < len(l_styles) else {}
                l_size = l_style.get('subtitle_size', subtitle_size)
                l_bold = l_style.get('subtitle_bold', subtitle_bold)
                l_font = get_font_for_line(l_size, l_bold)
                
                l_bbox = draw.textbbox((0, 0), line_text, font=l_font)
                l_w = l_bbox[2] - l_bbox[0]
                l_h = (l_bbox[3] - l_bbox[1]) + 15
                
                prepared_lines.append({
                    'text': line_text,
                    'font': l_font,
                    'color': color_map.get((l_style.get('subtitle_color') or subtitle_color).lower(), (255, 255, 255)),
                    'bg_visible': l_style.get('subtitle_bg_visible', subtitle_bg_visible),
                    'width': l_w,
                    'height': l_h
                })
                total_height += l_h

            if subtitle_position == 'center':
                y_start = (img.height - total_height) // 2
            else: # bottom
                y_start = img.height - total_height - (img.height * 0.15)
            
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            box_fill = (0, 0, 0, 160)
            
            current_y = y_start
            for l_data in prepared_lines:
                if l_data is None:
                    current_y += int(subtitle_size * 1.2)
                    continue
                lx = (img.width - l_data['width']) // 2
                if l_data['bg_visible']:
                    overlay_draw.rectangle(
                        [lx - padding, current_y, lx + l_data['width'] + padding, current_y + l_data['height']],
                        fill=box_fill
                    )
                overlay_draw.text((lx, current_y), l_data['text'], font=l_data['font'], fill=l_data['color'])
                current_y += l_data['height']
            
            # Rotation (Apply to both)
            if rotation != 0:
                img = img.rotate(-rotation, expand=True, resample=Image.BICUBIC)
                overlay = overlay.rotate(-rotation, expand=True, resample=Image.BICUBIC)
            
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay).convert('RGB')
            img.save(str(temp_image), "PNG", quality=95)
            
            # Now create video with this image
            cmd = [
                Config.get_ffmpeg(),
                "-loop", "1",
                "-r", "30",
                "-i", str(temp_image),
                "-i", audio_path,
                "-c:v", "libx264",
                "-r", "30",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={resolution.replace('x', ':')}:force_original_aspect_ratio=decrease,pad={resolution.replace('x', ':')}:(ow-iw)/2:(oh-ih)/2:color=black",
                "-af", f"atrim=0:{duration},apad=whole_dur={duration}",
                "-t", str(duration),
                "-shortest",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30, encoding='utf-8', errors='ignore')
            
            if temp_image.exists():
                temp_image.unlink()
            
            if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1024:
                logging.info(f"✓ Scene video with PIL fallback text created: {output_path}")
                return str(output_path)
            else:
                logging.error(f"PIL overlay FFmpeg failed: {result.stderr[:500]}")
                return None
            
        except Exception as e:
            logging.error(f"PIL fallback text overlay failed: {e}")
            return None
        
    async def _create_simple_scene_video(self, image_path: str, audio_path: str, 
                                       output_path: Path, duration: float, resolution: str = "1080x1920") -> Optional[str]:
        """Create a simple scene video without text overlay"""
        try:
            # Ensure the image exists
            if not Path(image_path).exists():
                logging.error(f"Image not found: {image_path}")
                return None
            
            # Ensure the audio exists
            if not Path(audio_path).exists():
                logging.error(f"Audio not found: {audio_path}")
                return None
            
            # Create a simple FFmpeg command
            cmd = [
                Config.get_ffmpeg(),
                "-loop", "1",
                "-r", "30",
                "-i", str(image_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-r", "30",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={resolution.replace('x', ':')}:force_original_aspect_ratio=decrease,pad={resolution.replace('x', ':')}:(ow-iw)/2:(oh-ih)/2:color=black",
                "-t", str(duration),
                "-shortest",
                "-y",
                str(output_path)
            ]
            
            logging.info(f"Creating simple scene video: {' '.join(cmd[:10])}...")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                logging.error(f"FFmpeg error for simple video: {result.stderr[:500]}")
                return None
            
            if output_path.exists():
                file_size = output_path.stat().st_size
                if file_size > 1024:
                    logging.info(f"✓ Simple scene video created: {output_path} ({file_size} bytes)")
                    return str(output_path)
                else:
                    logging.error(f"Scene video file is too small: {file_size} bytes")
                    return None
            else:
                logging.error("Scene video file was not created")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error("FFmpeg command timed out")
            return None
        except Exception as e:
            logging.error(f"Simple scene video creation failed: {e}")
            return None
        
    async def create_scene_video_with_subtitles(self, scene: Dict, audio_info: Dict, 
                                               visual_info: Dict, style: str) -> Optional[str]:
        """Create scene video using subtitle file approach"""
        try:
            scenes_dir = Config.STORAGE_DIR / "scenes"
            scenes_dir.mkdir(parents=True, exist_ok=True)
            
            scene_file = scenes_dir / f"scene_{scene['scene_number']}_{uuid.uuid4().hex[:6]}.mp4"
            
            # Create SRT subtitle file
            subtitle_file = Config.STORAGE_DIR / "temp" / f"sub_{uuid.uuid4().hex[:8]}.srt"
            subtitle_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Escape path for Windows
            subtitle_path_str = str(subtitle_file).replace('\\', '/').replace(':', '\\:')
            
            # Create simple subtitle
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write("1\n")
                f.write("00:00:00,000 --> 00:10:00,000\n")  # Long duration
                # Use voice_over for subtitles
                f.write(f"{scene.get('voice_over', scene.get('text', ''))}\n")
                f.write("\n")
            
            # FFmpeg command with subtitles - fix the f-string
            subtitle_filter = f"subtitles={subtitle_path_str}:force_style='Fontsize=42,PrimaryColour=&HFFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0'"
            
            cmd = [
                Config.get_ffmpeg(),
                "-loop", "1",
                "-i", visual_info["path"],
                "-i", audio_info["path"],
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                       f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
                       f"{subtitle_filter}",
                "-t", str(audio_info["duration"]),
                "-shortest",
                "-y",
                str(scene_file)
            ]
            
            logging.info("Creating video with subtitles...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Clean up subtitle file
            if subtitle_file.exists():
                subtitle_file.unlink()
            
            if result.returncode == 0 and scene_file.exists() and scene_file.stat().st_size > 1024:
                return str(scene_file)
            return None
            
        except Exception as e:
            logging.error(f"Subtitle video creation failed: {e}")
            return None    
        
    async def test_text_overlay(self):
        """Test if text overlay is working"""
        test_text = "Test overlay text for debugging"
        test_style = "default"
        
        # Create a test image
        test_img_path = Config.STORAGE_DIR / "test_image.png"
        img = self._create_base_image(test_style, 1080, 1920)
        img.save(str(test_img_path), "PNG")
        
        # Create test audio
        test_audio = await self.generate_audio("Test audio for debugging")
        
        # Test different methods
        print("Testing text overlay methods...")
        
        # Method 1: Direct FFmpeg
        print("\n1. Testing direct FFmpeg drawtext...")
        cmd = [
            Config.get_ffmpeg(),
            "-f", "lavfi",
            "-i", "color=c=blue:s=640x480:d=2",
            "-vf", f"drawtext=text='{test_text}':fontcolor=white:fontsize=24:x=20:y=20",
            "-t", "2",
            "-y",
            "test_ffmpeg.mp4"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ FFmpeg drawtext works")
        else:
            print(f"✗ FFmpeg drawtext failed: {result.stderr[:200]}")
        
        # Method 2: Check font availability
        print("\n2. Checking font availability...")
        fonts_to_check = [
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
        
        for font in fonts_to_check:
            if os.path.exists(font):
                print(f"✓ Font found: {font}")
            else:
                print(f"✗ Font not found: {font}")
        
        return True
    
    async def create_video(self, project_id: str, request: VideoCreateRequest):
        """Main video creation pipeline"""
        project = self.projects.get(project_id)
        if not project:
            return
        
        project["progress"] = 5
        project["status_message"] = "Starting video creation..."
        self.save_projects()
        
        try:
            # Use provided scenes if available, otherwise split script
            if request.scenes:
                scenes = request.scenes
                logging.info(f"Using {len(scenes)} provided scenes for project {project_id}")
            else:
                scenes = self.script_processor.split_script(request.script, request.scenes_count)
                # Enrich with voice-overs matching the language
                scenes = await self.script_processor.enrich_scenes_with_voiceover(scenes, request.language)
            project["scenes"] = scenes
            
            
            # Generate assets for each scene
            scene_videos = []
            total_scenes = len(scenes)
            
            for i, scene in enumerate(scenes):
                # Update progress
                progress = 10 + int((i / total_scenes) * 70)
                project["progress"] = progress
                project["status_message"] = f"Generating scene {i+1}/{total_scenes}..."
                
                # Generate audio
                # Priority:
                # 1. Custom uploaded audio
                # 2. AI Generated voice_over
                # 3. Silent audio
                custom_audio_path = scene.get("custom_audio_path")
                show_image_only = scene.get("show_image_only", False)
                
                if custom_audio_path and os.path.exists(custom_audio_path):
                    logging.info(f"Using custom audio for scene {i+1}: {custom_audio_path}")
                    duration = self._get_audio_duration(Path(custom_audio_path))
                    audio_info = {
                        "path": custom_audio_path,
                        "duration": duration,
                        "url": scene.get("custom_audio_url", "")
                    }
                elif not show_image_only and scene.get("voice_over", scene.get("text")):
                    voice_text = scene.get("voice_over", scene["text"])
                    
                    # CACHING LOGIC: Skip AI call if text/voice is unchanged and file exists
                    existing_audio = scene.get("audio_info")
                    is_local_reuse = (
                        existing_audio and 
                        existing_audio.get("path") and 
                        os.path.exists(existing_audio["path"]) and
                        existing_audio.get("generation_text") == voice_text and
                        existing_audio.get("voice_id") == request.voice
                    )
                    
                    if is_local_reuse:
                        logging.info(f"Credit Saver: Fast-reusing local audio for scene {i+1}")
                        audio_info = existing_audio
                        project["status_message"] = f"Reusing local audio for scene {i+1}/{total_scenes} (Credit saved!)"
                    else:
                        # Even if local file is missing, generate_audio will check S3 cache
                        logging.info(f"Checking cache/generating audio for scene {i+1}")
                        project["status_message"] = f"Preparing audio for scene {i+1}/{total_scenes}..."
                        audio_info = await self.generate_audio(voice_text, request.language, request.voice)
                        
                        if audio_info.get("cached"):
                            project["status_message"] = f"Audio cache hit for scene {i+1}/{total_scenes} (Credit saved!)"
                        else:
                            project["status_message"] = f"Generated new audio for scene {i+1}/{total_scenes}"
                        
                        if audio_info.get("error_code") == "QUOTA_EXCEEDED":
                            raise VideoPipelineError(
                                "ElevenLabs Credits Exhausted",
                                code="ELEVENLABS_QUOTA",
                                details="Your account has run out of credits. Please top up your ElevenLabs account.",
                                action="UPGRADE_PLAN"
                            )
                        
                        if audio_info.get("path"):
                            scene["audio_info"] = audio_info
                else:
                    # Create silent audio for the specified duration
                    audio_info = await self._create_silent_audio(scene.get("duration", 5.0))
                
                if not audio_info.get("path"):
                    logging.error(f"Failed to generate audio for scene {i+1}")
                    continue
                
                # Generate visual
                visual_info = await self.generate_visual(
                    scene.get("visual_prompt", scene["text"]),
                    request.image_style,
                    scene["scene_number"],
                    request.resolution,
                    custom_image_path=scene.get("custom_image_path")
                )
                if not visual_info["path"]:
                    logging.error(f"Failed to generate visual for scene {i+1}")
                    continue
                
                # Create scene video
                scene_video_path = await self.create_scene_video(
                    scene, audio_info, visual_info, request.image_style, request.resolution, request.language,
                    subtitle_style=request.subtitle_style
                )
                
                if scene_video_path and Path(scene_video_path).exists():
                    file_size = Path(scene_video_path).stat().st_size
                    if file_size > 1024:
                        scene_videos.append(scene_video_path)
                        logging.info(f"Added scene video {scene_video_path} ({file_size} bytes)")
                    else:
                        logging.warning(f"Scene video too small: {scene_video_path}")
                else:
                    logging.warning(f"Failed to create scene video for scene {i+1}")
            
            # Concatenate all scene videos
            project["progress"] = 85
            project["status_message"] = "Combining scenes into final video..."
            
            # Determine if we should use demuxer (for complex scripts with ASS subtitles)
            use_demuxer = request.language in ComplexScriptRenderer.COMPLEX_SCRIPTS
            
            video_url, video_s3_key = await self._concatenate_videos(scene_videos, request.resolution, use_demuxer=use_demuxer)
            
            # Update project
            project["progress"] = 100
            project["status"] = "completed" if video_url else "failed"
            project["video_url"] = video_url
            project["video_s3_key"] = video_s3_key
            project["completed_at"] = datetime.now().isoformat()
            
            self._save_projects()
            
            if video_url:
                if video_url.startswith('http'):
                    project["status_message"] = "Video created successfully and stored in cloud"
                    logging.info(f"Final video created and uploaded to S3: {video_url}")
                else:
                    video_path = Config.STORAGE_DIR / video_url.replace('/storage/', '')
                    if video_path.exists():
                        file_size = video_path.stat().st_size
                        project["status_message"] = f"Video created successfully ({file_size/1024/1024:.1f} MB)"
                        logging.info(f"Final video created: {video_path} ({file_size} bytes)")
                    else:
                        project["status_message"] = "Video created but local file not found"
                        project["status"] = "failed"
            else:
                project["status_message"] = "Failed to create video"
                project["status"] = "failed"
            
            self.save_projects()
            
        except Exception as e:
            logging.error(f"Video creation failed: {e}", exc_info=True)
            project["status"] = "failed"
            
            if isinstance(e, VideoPipelineError):
                project["error"] = e.to_dict()
                project["status_message"] = e.message
            else:
                # Generic fallback
                project["error"] = {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": str(e),
                    "action": "RETRY"
                }
                project["status_message"] = f"Error: {str(e)}"
            self.save_projects()
    
    async def _concatenate_videos(self, video_files: List[str], resolution: str, use_demuxer: bool = False) -> str:
        """Concatenate multiple videos into one"""
        try:
            if not video_files:
                logging.error("No video files to concatenate")
                # Instead of fallback, strict error
                raise VideoConcatenationError("No valid video files to concatenate")
            
            video_id = f"video_{uuid.uuid4().hex[:8]}"
            
            # Filter valid videos
            valid_videos = []
            for video in video_files:
                if video and Path(video).exists():
                    size = Path(video).stat().st_size
                    if size > 1024:  # At least 1KB
                        valid_videos.append(video)
                        logging.info(f"Valid video: {video} ({size} bytes)")
                    else:
                        logging.warning(f"Skipping small video: {video} ({size} bytes)")
            
            if not valid_videos:
                raise VideoConcatenationError("No valid videos to concatenate after filtering")
            
            if use_demuxer:
                logging.info(f"Using Concat Demuxer for {len(valid_videos)} videos (ASS Subtitles)...")
                video_file_path = await self._concatenate_with_demuxer(valid_videos, video_id)
            else:
                logging.info(f"Using Filter Complex for {len(valid_videos)} videos (Standard)...")
                video_file_path = await self._concatenate_with_filter_complex(valid_videos, video_id, resolution)
            
            if video_file_path:
                output_path = Path(video_file_path)
                s3_key = f"videos/{output_path.name}"
                if Config.USE_S3:
                    if Config.s3.upload_file(output_path, s3_key):
                        logging.info(f"✓ Video successfully persistent in S3: {s3_key}")
                        return Config.s3.get_url(s3_key), s3_key
                    else:
                        logging.error(f"Failed to upload video to S3: {s3_key}. Using local fallback.")
                        return f"/storage/videos/{output_path.name}", None
                return f"/storage/videos/{output_path.name}", None
            return None, None
                
        except Exception as e:
            if isinstance(e, VideoPipelineError): raise e
            logging.error(f"Video concatenation failed: {e}")
            raise VideoConcatenationError(f"Concatenation failed: {e}")


    async def _concatenate_with_demuxer(self, video_files: List[str], video_id: str) -> str:
        """
        Concatenate using the concat demuxer (no re-encoding).
        Recommended for videos with burned ASS subtitles to avoid EINVAL errors.
        """
        try:
            output_file = Config.STORAGE_DIR / "videos" / f"{video_id}.mp4"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create concat file
            concat_file = Config.STORAGE_DIR / "temp" / f"concat_{video_id}.txt"
            concat_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write absolute paths to concat file
            with open(concat_file, 'w', encoding='utf-8') as f:
                for video in video_files:
                    # FFmpeg concat requires forward slashes and escaped quotes
                    path_str = str(Path(video).absolute()).replace('\\', '/').replace("'", "'\\''")
                    f.write(f"file '{path_str}'\n")
            
            cmd = [
                Config.get_ffmpeg(),
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                "-y",
                str(output_file)
            ]
            
            await self.run_ffmpeg_safe(cmd, timeout=300, context=f"Demuxer Concatenation ({len(video_files)} files)")
            
            if output_file.exists():
                file_size = output_file.stat().st_size
                if file_size > 1024:
                    logging.info(f"✓ Demuxer Concatenation successful. Size: {file_size} bytes")
                    return str(output_file)
                else:
                    raise VideoConcatenationError("Concatenation produced empty video file", f"Size: {file_size} bytes")
            else:
                 raise VideoConcatenationError("Concatenation output file not found", str(output_file))
                 
        except Exception as e:
            if isinstance(e, VideoPipelineError): raise e
            raise VideoConcatenationError(f"Demuxer concatenation failed: {e}")
    
    async def _concatenate_with_filter_complex(self, video_files: List[str], video_id: str, resolution: str) -> str:
        """Alternative concatenation method using filter complex"""
        try:
            output_file = Config.STORAGE_DIR / "videos" / f"{video_id}.mp4"
            
            # Build ffmpeg command with inputs
            cmd = [Config.get_ffmpeg()]
            
            # Add all video files as inputs
            for video in video_files:
                cmd.extend(["-i", video])
            
            # Build filter complex with stream normalization
            filter_parts = []
            for i in range(len(video_files)):
                # Normalize each stream: constant frame rate and constant sample rate
                filter_parts.append(f"[{i}:v]fps=30,format=yuv420p[v{i}];")
                filter_parts.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];")
            
            # Concatenate normalized streams
            concat_inputs = ""
            for i in range(len(video_files)):
                concat_inputs += f"[v{i}][a{i}]"
            
            concat_filter = f"{concat_inputs}concat=n={len(video_files)}:v=1:a=1[outv][outa]"
            filter_complex = "".join(filter_parts) + concat_filter
            
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-r", "30",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-movflags", "+faststart",
                "-y",
                str(output_file)
            ])
            
            # Use safe wrapper with 300s timeout
            await self.run_ffmpeg_safe(cmd, timeout=300, context=f"Concatenating {len(video_files)} videos")
            
            if output_file.exists():
                file_size = output_file.stat().st_size
                if file_size > 1024:
                    logging.info(f"✓ Concatenation successful. Size: {file_size} bytes")
                    return str(output_file)
                else:
                    raise FFmpegError("Concatenation produced empty video file", f"Size: {file_size} bytes")
            else:
                 raise FFmpegError("Concatenation output file not found", str(output_file))
            
        except Exception as e:
            if isinstance(e, VideoPipelineError): raise e
            logging.error(f"Filter complex concatenation failed: {e}")
            raise FFmpegError(f"Concatenation failed: {e}")
    
    def _create_fallback_video(self, resolution: str) -> str:
        """Create a fallback video when everything else fails"""
        try:
            video_id = f"fallback_{uuid.uuid4().hex[:8]}"
            output_file = Config.STORAGE_DIR / "videos" / f"{video_id}.mp4"
            
            width, height = map(int, resolution.split('x'))
            
            # Create a simple color video with text
            cmd = [
                Config.get_ffmpeg(),
                "-f", "lavfi",
                "-i", f"color=c=#667eea:s={width}x{height}:d=5",
                "-vf", "drawtext=text='Video Preview':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264",
                "-t", "5",
                "-pix_fmt", "yuv420p",
                "-y",
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and output_file.exists():
                file_size = output_file.stat().st_size
                if file_size > 1024:
                    return f"/storage/videos/{video_id}.mp4"
            
            return ""
                
        except Exception as e:
            logging.error(f"Fallback video creation failed: {e}")
            return ""
        
# ========== FASTAPI APP ==========
app = FastAPI(
    title="Faceless Videos Creator",
    description="Create videos from your script automatically",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage
app.mount("/storage", StaticFiles(directory=Config.STORAGE_DIR), name="storage")

# Initialize generator
video_gen = VideoGenerator()

# ========== API ENDPOINTS ==========

@app.get("/")
async def root():
    return {
        "message": "Faceless Videos Creator API v2",
        "version": "2.0.0",
        "features": [
            "Single script input - we auto-split into scenes",
            "10 different voices with audio",
            "Pexels realistic image style",
            "Video with audio, images, and text overlay",
            "Multiple languages support"
        ]
    }

@app.get("/api/config")
async def get_config():
    """Get all configuration options"""
    return {
        "success": True,
        "data": {
            "voices": video_gen.get_voices(),
            "image_styles": video_gen.get_image_styles(),
            "languages": ["en", "es", "fr", "de", "it", "pt", "hi", "ar", "zh", "ja", "ko", "ta"],
            "tones": ["neutral", "professional", "casual", "humorous", "educational", "motivational"],
            "resolutions": ["720x1280", "1080x1920", "1440x2560"],
            "max_scenes": 16,
            "min_scenes": 4
        }
    }

# Lifecycle events
# Original startup_event removed in favor of combined_startup_event at bottom of file

@app.post("/api/videos/create")
async def create_video(request: VideoCreateRequest, background_tasks: BackgroundTasks):
    project_id = str(uuid.uuid4())
    
    # Track the full request data for re-editing
    video_gen.projects[project_id] = {
        "id": project_id,
        "title": request.title,
        "status": "processing",
        "progress": 0,
        "video_url": None,
        "created_at": datetime.now().isoformat(),
        "request_data": request.model_dump()
    }
    
    video_gen._save_projects()
    background_tasks.add_task(video_gen.create_video, project_id, request)
    return {"success": True, "data": {"project_id": project_id}}

@app.get("/api/projects")
async def get_projects():
    """List all projects sorted by date"""
    try:
        # Convert dict to list items suitable for front-end preview
        history = []
        for pid, p in video_gen.projects.items():
            video_url = p.get("video_url")
            s3_key = p.get("video_s3_key")
            
            # Refresh presigned URL if it's an S3 video
            if Config.USE_S3 and s3_key:
                video_url = Config.s3.get_url(s3_key)
                
            history.append({
                "id": pid,
                "title": p.get("title", "Untitled"),
                "status": p.get("status", "unknown"),
                "created_at": p.get("created_at"),
                "video_url": video_url,
                "progress": p.get("progress", 0)
            })
        
        # Sort by date descending
        history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"success": True, "data": history}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/projects/{project_id}")
async def get_project_details(project_id: str):
    """Get full details of a specific project for re-editing"""
    project = video_gen.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Refresh presigned URL
    s3_key = project.get("video_s3_key")
    if Config.USE_S3 and s3_key:
        project["video_url"] = Config.s3.get_url(s3_key)
        
    return {"success": True, "data": project}
        
@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """Get project status"""
    project = video_gen.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Refresh presigned URL
    s3_key = project.get("video_s3_key")
    if Config.USE_S3 and s3_key:
        project["video_url"] = Config.s3.get_url(s3_key)
        
    return {
        "success": True,
        "data": project
    }

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and its associated video file"""
    try:
        project = video_gen.projects.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete physical video file if it exists
        video_url = project.get("video_url")
        if video_url:
            if "amazonaws.com" in video_url:
                # S3 URL: Extract key
                # Format: https://bucket.s3.region.amazonaws.com/videos/filename.mp4
                try:
                    # Extract everything after the hostname
                    s3_key = video_url.split(".com/")[-1]
                    Config.s3.delete_file(s3_key)
                except Exception as e:
                    logging.warning(f"Could not parse S3 URL {video_url} for deletion: {e}")
            else:
                # Local storage
                video_path = Config.STORAGE_DIR / video_url.replace('/storage/', '')
                if video_path.exists():
                    try:
                        video_path.unlink()
                        logging.info(f"Deleted local video file: {video_path}")
                    except Exception as e:
                        logging.warning(f"Could not delete local video file {video_path}: {e}")
        
        # Remove from projects dict
        del video_gen.projects[project_id]
        video_gen._save_projects()
        
        return {"success": True, "message": "Project deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Update the preview endpoints to return proper data
@app.post("/api/audio/set-default")
async def set_audio_default(request: Dict[str, Any]):
    """Promote a generated audio file to a system-wide default"""
    try:
        path = request.get("path")
        audio_type = request.get("type") # 'intro' or 'outro'
        
        if not path:
            raise UserInputError("Path is required")
            
        # If it's an S3 key, we might need to download it for metadata calculation
        # but path should be local according to our VideoGenerator refactor
        if not os.path.exists(path):
            if Config.USE_S3 and Config.s3.exists(path):
                # Download to temp
                temp_p = Config.STORAGE_DIR / "temp" / Path(path).name
                Config.s3.download_file(path, temp_p)
                path = str(temp_p)
            else:
                raise UserInputError(f"Audio file not found: {path}")
            
        if audio_type not in ["intro", "outro"]:
            raise UserInputError("Type must be 'intro' or 'outro'")
            
        dest_filename = f"default_{audio_type}.mp3"
        dest_path = Config.STORAGE_DIR / "system_defaults" / dest_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to system defaults locally
        shutil.copy2(path, dest_path)
        
        # Calculate duration
        duration = video_gen._get_audio_duration(Path(path))
        
        # S3 Persistence
        s3_key = f"system_defaults/{dest_filename}"
        s3_meta_key = f"system_defaults/default_{audio_type}.json"
        
        url = f"/storage/system_defaults/{dest_filename}"
        if Config.USE_S3:
            Config.s3.upload_file(dest_path, s3_key)
            url = Config.s3.get_url(s3_key)
        
        # Save metadata JSON
        meta_data = {
            "path": s3_key if Config.USE_S3 else str(dest_path),
            "url": url,
            "duration": duration,
            "text": request.get("text", ""),
            "type": audio_type,
            "timestamp": datetime.now().isoformat()
        }
        
        meta_path = dest_path.with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump(meta_data, f)
            
        if Config.USE_S3:
            Config.s3.upload_file(meta_path, s3_meta_key)
            
        return {
            "success": True,
            "message": f"Successfully set system default {audio_type}",
            "data": {
                "url": url,
                "duration": duration
            }
        }
    except Exception as e:
        logging.error(f"Failed to set audio default: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/visuals/preview")
async def preview_visual(
    text: str = Form(...),
    style: str = Form("default"),
    scene_number: int = Form(1)
):
    """Preview visual generation"""
    try:
        visual_info = await video_gen.generate_visual(text, style, scene_number)
        return {
            "success": True,
            "data": {
                "url": visual_info["url"],
                "style": visual_info["style"],
                "text": text[:100] + "..." if len(text) > 100 else text
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ... (previous imports and code remain the same)

@app.post("/api/scripts/preview")
async def preview_script_split(request: Dict[str, Any]):
    """Preview how script will be split into scenes"""
    try:
        script = request.get("script", "")
        scenes_count = request.get("scenes_count", 8)
        language = request.get("language", "en")
        
        processor = ScriptProcessor()
        scenes = processor.split_script(script, scenes_count)
        
        # Enrich with voice-overs
        scenes = await processor.enrich_scenes_with_voiceover(scenes, language)
        
        return {
            "success": True,
            "data": {
                "total_scenes": len(scenes),
                "scenes": scenes,
                "script_preview": script[:500] + "..." if len(script) > 500 else script
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Alternative version if you want to use Form data (as in original):
@app.post("/api/scripts/preview/form")
async def preview_script_split_form(
    script: str = Form(...),
    scenes_count: int = Form(8),
    language: str = Form("en")
):
    """Preview how script will be split into scenes (Form version)"""
    try:
        processor = ScriptProcessor()
        scenes = processor.split_script(script, scenes_count)
        
        # Enrich with voice-overs
        scenes = await processor.enrich_scenes_with_voiceover(scenes, language)
        
        return {
            "success": True,
            "data": {
                "total_scenes": len(scenes),
                "scenes": scenes,
                "script_preview": script[:500] + "..." if len(script) > 500 else script
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/audio/preview")
async def preview_audio(request: Dict[str, Any]):
    """Preview audio generation"""
    try:
        text = request.get("text", "")
        language = request.get("language", "en")
        
        voice_id = request.get("voice")
        logging.info(f"Audio Preview Request: voice={voice_id}, language={language}")
        audio_info = await video_gen.generate_audio(text, language, voice_id)
        return {
            "success": True,
            "data": {
                "url": audio_info["url"],
                "path": audio_info["path"],
                "duration": audio_info["duration"],
                "text": text[:100] + "..." if len(text) > 100 else text
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/test/text-overlay")
async def test_text_overlay():
    """Test text overlay functionality"""
    result = await video_gen.test_text_overlay()
    return {"success": True, "message": "Test completed", "result": result}
 
@app.get("/api/download/{video_filename}")
async def download_video(video_filename: str):
    """Download generated video"""
    video_path = Config.STORAGE_DIR / "videos" / video_filename
    
    # If not found locally, try to download from S3
    if not video_path.exists():
        s3_key = f"videos/{video_filename}"
        if Config.USE_S3 and Config.s3.exists(s3_key):
            logging.info(f"Downloading {video_filename} from S3 for local download request")
            Config.s3.download_file(s3_key, video_path)
        
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        video_path,
        filename=video_filename,
        media_type='video/mp4'
    )

@app.post("/api/upload/scene-audio")
async def upload_scene_audio(file: UploadFile = File(...)):
    """Upload a custom audio file for a scene"""
    try:
        # Create audio directory if it doesn't exist
        audio_dir = Config.STORAGE_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename
        file_extension = Path(file.filename).suffix
        if not file_extension:
            file_extension = ".mp3"
        
        filename = f"custom_voice_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = audio_dir / filename
        
        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Get duration
        duration = video_gen._get_audio_duration(file_path)
        
        # S3 Support
        s3_key = f"audio/{filename}"
        url = f"/storage/audio/{filename}"
        if Config.USE_S3:
            Config.s3.upload_file(file_path, s3_key)
            url = Config.s3.get_url(s3_key)

        return {
            "success": True,
            "data": {
                "url": url,
                "path": str(file_path),
                "s3_key": s3_key if Config.USE_S3 else None,
                "duration": duration
            }
        }
    except Exception as e:
        logging.error(f"Failed to upload scene audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/scene-image")
async def upload_scene_image(file: UploadFile = File(...)):
    """Upload a custom image for a scene"""
    try:
        # Create visuals directory if it doesn't exist
        visuals_dir = Config.STORAGE_DIR / "visuals"
        visuals_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename
        file_extension = Path(file.filename).suffix
        if not file_extension:
            file_extension = ".png"
        
        filename = f"custom_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = visuals_dir / filename
        
        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # S3 Support
        s3_key = f"visuals/{filename}"
        url = f"/storage/visuals/{filename}"
        if Config.USE_S3:
            Config.s3.upload_file(file_path, s3_key)
            url = Config.s3.get_url(s3_key)

        return {
            "success": True,
            "data": {
                "url": url,
                "path": str(file_path),
                "s3_key": s3_key if Config.USE_S3 else None
            }
        }
    except Exception as e:
        logging.error(f"Failed to upload scene image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== FACEBOOK ROUTES ==========

@app.get("/api/facebook/integrations")
async def get_fb_integrations(db: Session = Depends(get_db)):
    """List connected Facebook pages (DEPRECATED - Use Postiz integrations instead)"""
    integrations = db.query(Integration).filter(Integration.is_active == True).all()
    # Serialize for JSON
    data = []
    for integration in integrations:
        data.append({
            "id": integration.id,
            "name": integration.name,
            "internal_id": integration.internal_id,
            "picture": integration.picture,
            "provider": integration.provider
        })
    return {"success": True, "data": data}

@app.post("/api/facebook/post-now")
async def fb_post_now(
    project_id: str = Form(...),
    integration_id: str = Form(...),
    caption: str = Form(""),
    db: Session = Depends(get_db)
):
    """Immediately post a video to Facebook"""
    project = video_gen.projects.get(project_id)
    if not project or project.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Project not found or video not ready")
    
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration (Page) not found")
    
    video_url = project.get("video_url")
    video_path = str(Config.STORAGE_DIR / video_url.replace('/storage/', ''))
    
    try:
        result = facebook_manager.post_video(
            page_id=integration.internal_id,
            page_access_token=integration.access_token,
            video_path=video_path,
            title=project.get("title", "Generated Video"),
            description=caption or project.get("title", "")
        )
        return {"success": True, "fb_post_id": result.get("id")}
    except Exception as e:
        logging.error(f"FB Post Now Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/facebook/schedule")
async def fb_schedule(
    project_id: str = Form(...),
    integration_id: str = Form(...),
    schedule_time: str = Form(...), # ISO format
    caption: str = Form(""),
    db: Session = Depends(get_db)
):
    """Schedule a video to be posted later"""
    project = video_gen.projects.get(project_id)
    if not project or project.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Project not found or video not ready")
    
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration (Page) not found")
    
    try:
        st_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
        # Convert to UTC naive for storage
        utc_dt = st_dt.astimezone(timezone.utc).replace(tzinfo=None)
        
        if st_dt <= datetime.now(st_dt.tzinfo):
            raise ValueError("Scheduled time must be in the future")

        video_url = project.get("video_url")
        video_path = str(Config.STORAGE_DIR / video_url.replace('/storage/', ''))

        post = ScheduledPost(
            id=f"post_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            integration_id=integration_id,
            video_path=video_path,
            caption=caption or project.get("title", ""),
            schedule_time=utc_dt,
            status="scheduled"
        )
        db.add(post)
        db.commit()
        return {"success": True, "post_id": post.id}
    except Exception as e:
        logging.error(f"FB Schedule Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/facebook/scheduled-posts")
async def get_scheduled_posts(db: Session = Depends(get_db)):
    """Fetch all scheduled and recently posted videos"""
    try:
        posts = db.query(ScheduledPost).order_by(ScheduledPost.schedule_time.desc()).all()
        data = []
        for post in posts:
            data.append({
                "id": post.id,
                "project_id": post.project_id,
                "integration_name": post.integration.name if post.integration else "Unknown",
                "integration_picture": post.integration.picture if post.integration else None,
                "caption": post.caption,
                "schedule_time": post.schedule_time.isoformat() + 'Z' if post.schedule_time else None,
                "status": post.status,
                "error_message": post.error_message,
                "fb_permalink": post.fb_permalink
            })
        return {"success": True, "data": data}
    except Exception as e:
        logging.error(f"Error fetching scheduled posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== RUN SERVER ==========

import asyncio
import uuid
import logging
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# ==============================================================================
# POSTIZ INTEGRATION ENDPOINTS
# ==============================================================================

try:
    from postiz_client import PostizClient
except ImportError:
    logging.warning("Could not import PostizClient. Integration will be disabled.")
    PostizClient = None

postiz_client = None
postiz_auth_service = PostizAuthService(
    base_url=Config.POSTIZ_BASE_URL,
    jwt_secret=Config.POSTIZ_JWT_SECRET
)

@app.on_event("startup")
async def combined_startup_event():
    import sys
    print("COMBINED STARTUP: Initializing...", flush=True, file=sys.stderr)
    
    # 1. Initialize DB
    try:
        # Force File Logging (Uvicorn override fix)
        import logging
        root_logger = logging.getLogger()
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        
        init_db()
        print("COMBINED STARTUP: DB Initialized.", flush=True, file=sys.stderr)
    except Exception as e:
        print(f"STARTUP DB ERROR: {e}", flush=True, file=sys.stderr)
        import traceback
        traceback.print_exc()

    # 2. Initialize Postiz Client & Scheduler
    global postiz_client
    if Config.POSTIZ_ENABLED and Config.POSTIZ_API_KEY and PostizClient:
        try:
            postiz_client = PostizClient(
                api_key=Config.POSTIZ_API_KEY,
                base_url=Config.POSTIZ_BASE_URL
            )
            # Initialize session
            await postiz_client.__aenter__() 
            logging.info(f"Postiz Client initialized at {Config.POSTIZ_BASE_URL}")
            
            # Start Scheduler with Client
            start_scheduler(client=postiz_client)
            print("COMBINED STARTUP: Scheduler Started with Client.", flush=True, file=sys.stderr)
            
            # Pre-fetch user ID for headless auth
            if Config.POSTIZ_JWT_SECRET:
                # Run in background to not block startup
                asyncio.create_task(asyncio.to_thread(postiz_auth_service.get_user_id))
        except Exception as e:
            logging.error(f"Failed to initialize Postiz client: {e}")
            # Start scheduler without client (warns in logs)
            start_scheduler(client=None)
    else:
        start_scheduler(client=None)
        print("COMBINED STARTUP: Scheduler Started (No Client).", flush=True, file=sys.stderr)

@app.on_event("shutdown")
async def shutdown_event():
    if postiz_client:
        await postiz_client.close()

@app.get("/api/postiz/integrations")
async def get_postiz_integrations(
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    if not postiz_client:
         raise HTTPException(status_code=400, detail="Postiz integration disabled")
    
    if not force_refresh:
        cached = db.query(PostizIntegration).filter(PostizIntegration.enabled == True).all()
        if cached:
            return {"success": True, "data": [{"id": i.id, "name": i.name, "platform": i.platform, "enabled": i.enabled} for i in cached]}

    try:
        integrations = await postiz_client.get_integrations()
        
        # Get current API IDs
        api_ids = [i.get('id') for i in integrations]
        
        # Sync to DB
        for integration in integrations:
             # Postiz 1.0/2.0 compat
             pid = integration.get('platform') or integration.get('identifier') or integration.get('type') or integration.get('providerIdentifier') or integration.get('provider') or 'unknown'
             iid = integration.get('id')
             name = integration.get('name', 'Unknown')
             disabled = integration.get('disabled', False)
             
             db_int = db.query(PostizIntegration).filter(PostizIntegration.id == iid).first()
             
             # Skip unknown platforms
             if pid == 'unknown':
                 logging.warning(f"Skipping integration {name} ({iid}) with unknown platform")
                 continue
                 
             if not db_int:
                 db_int = PostizIntegration(id=iid, name=name, platform=pid, enabled=not disabled)
                 db.add(db_int)
             else:
                 db_int.name = name
                 db_int.platform = pid
                 db_int.enabled = not disabled
                 db_int.last_synced = datetime.utcnow()
        
        # Remove deleted integrations
        if api_ids:
            db.query(PostizIntegration).filter(PostizIntegration.id.notin_(api_ids)).delete(synchronize_session=False)
        elif integrations == []: # If API returns empty list, clear all
            db.query(PostizIntegration).delete()
            
        db.commit()
        return {"success": True, "data": integrations}
    except Exception as e:
        logging.error(f"Postiz Sync Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/postiz/integrations/{integration_id}")
async def delete_postiz_integration(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """Delete an integration from Postiz (Headless)"""
    if not postiz_client:
        raise HTTPException(status_code=400, detail="Postiz integration disabled")
    
    try:
        # 1. Delete from Postiz
        await postiz_client.delete_integration(integration_id)
        
        # 2. Delete from local DB cache
        db.query(PostizIntegration).filter(PostizIntegration.id == integration_id).delete()
        db.commit()
        
        return {"success": True, "message": "Integration deleted successfully"}
    except Exception as e:
        logging.error(f"Postiz Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/postiz/auth-url/{provider}")
async def get_postiz_auth_url(provider: str, callback_url: str):
    """Get the OAuth URL for a provider from Postiz (Headless)"""
    if not Config.POSTIZ_ENABLED:
        raise HTTPException(status_code=400, detail="Postiz integration disabled")
    if not Config.POSTIZ_JWT_SECRET:
         raise HTTPException(status_code=500, detail="JWT_SECRET not configured for Postiz Auth")

    result = await postiz_auth_service.get_auth_url(provider, callback_url)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/postiz/connect/{provider}")
async def connect_postiz_account(provider: str, payload: Dict[str, str]):
    """Complete the connection flow after OAuth callback"""
    code = payload.get("code")
    state = payload.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
        
    result = await postiz_auth_service.complete_connection(provider, code, state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("details", result["error"]))
    return {"success": True, "data": result}

@app.post("/api/postiz/connect/{integration_id}/page")
async def connect_postiz_page(integration_id: str, payload: Dict[str, str]):
    """Complete the connection for a two-step provider (like Facebook) by selecting a page"""
    state = payload.get("state")
    page_id = payload.get("page")
    if not state or not page_id:
        raise HTTPException(status_code=400, detail="Missing state or page_id")
        
    result = await postiz_auth_service.complete_page_connection(integration_id, state, page_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("details", result["error"]))
    return {"success": True, "data": result}

class ScheduleRequest(BaseModel):
    video_id: str
    caption: str
    platform_ids: List[str]
    schedule_time: Optional[datetime] = None

@app.post("/api/postiz/upload-and-schedule")
async def upload_and_schedule(
    req: ScheduleRequest,
    db: Session = Depends(get_db)
):
    if not postiz_client:
        raise HTTPException(status_code=400, detail="Postiz integration disabled")
        
    # Locate Video
    video_path = None
    # Check absolute path in storage
    possible_path = Config.STORAGE_DIR / "videos" / f"{req.video_id}.mp4"
    if possible_path.exists():
        video_path = possible_path
    elif (Config.STORAGE_DIR / "videos" / req.video_id).exists():
        video_path = Config.STORAGE_DIR / "videos" / req.video_id
    elif (Config.STORAGE_DIR / req.video_id).exists():
         video_path = Config.STORAGE_DIR / req.video_id  
    
    if not video_path:
        # Try finding by project ID
        project = video_gen.projects.get(req.video_id)
        if project and project.get("video_url"):
            # video_url is like /storage/videos/video_xxx.mp4
            # We need absolute path
            relative_path = project["video_url"].lstrip("/")
            if relative_path.startswith("storage/"):
                 possible_path = Config.STORAGE_DIR / relative_path.replace("storage/", "")
            else:
                 possible_path = Config.STORAGE_DIR / relative_path
            
            if possible_path.exists():
                video_path = possible_path

    if not video_path:
        raise HTTPException(status_code=404, detail=f"Video file not found for ID: {req.video_id}")

    try:
        # NEW LOGIC: Just save to DB. Scheduler picks it up.
        logging.info(f"Queueing post for scheduling: Video {req.video_id}")
        
        # Normalize schedule_time to UTC Naive for storage consistency
        if req.schedule_time:
            # Ensure it is UTC
            utc_dt = req.schedule_time
            if utc_dt.tzinfo is None:
                 utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            else:
                 utc_dt = utc_dt.astimezone(timezone.utc)
            
            # Store as naive UTC
            storage_dt = utc_dt.replace(tzinfo=None)
        else:
            storage_dt = datetime.utcnow()

        # Save Record with postiz_status="SCHEDULED" (or "PICKUP" if immediate? No, let scheduler decide)
        # Status "scheduled" is legacy status. "postiz_status" drives the new machine.
        
        rec = ScheduledPost(
            id=f"post_{uuid.uuid4().hex[:8]}",
            project_id=req.video_id,
            video_path=str(video_path), # Save path so scheduler can upload
            caption=req.caption,
            platforms=",".join(req.platform_ids),
            integration_id=req.platform_ids[0] if req.platform_ids else None, # Legacy compatibility
            schedule_time=storage_dt,
            status='scheduled',
            postiz_status='SCHEDULED', # Triggers PICKUP loop
            postiz_post_id=None,
            postiz_media_id=None,
            retry_count=0,
            error_source=None
        )
        db.add(rec)
        db.commit()
        
        return {"success": True, "data": {"post_id": rec.id, "message": "Post queued for processing"}}
    except Exception as e:
        logging.error(f"Scheduling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/trigger")
async def trigger_scheduler_manual():
    """Manually trigger the scheduler check"""
    from scheduler import process_scheduled_posts
    logging.error("MANUAL SCHEDULER TRIGGER RECEIVED")
    try:
        await process_scheduled_posts()
        return {"success": True, "message": "Scheduler triggered"}
    except Exception as e:
         logging.error(f"Manual trigger failed: {e}")
         raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduled-posts")
async def get_scheduled_posts_endpoint(db: Session = Depends(get_db)):
    posts = db.query(ScheduledPost).order_by(ScheduledPost.created_at.desc()).all()
    data = []
    for p in posts:
        if p.schedule_time:
            # Force UTC if naive, otherwise convert to UTC string with Z
            dt = p.schedule_time
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            schedule_time_str = dt.isoformat().replace("+00:00", "Z")
        else:
            schedule_time_str = None
            
        data.append({
            "id": p.id,
            "caption": p.caption,
            "schedule_time": schedule_time_str,
            "status": p.status,
            "platforms": p.platforms.split(',') if p.platforms else [],
            "video_id": p.project_id,
            "postiz_status": p.postiz_status, # New field
            "error_source": p.error_source, # New field
            "last_error_message": p.last_error_message # New field
        })
    return {"success": True, "data": data}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    print("=" * 50)
    print(f"🎬 FACELESS VIDEOS BACKEND running on port {port}")
    print("=" * 50)
    print(f"Server starting on: http://localhost:{port}")
    print(f"API Documentation: http://localhost:{port}/docs")
    print(f"Storage directory: {Config.STORAGE_DIR}")
    print("\nFeatures:")
    print("• Single script input - auto-split into scenes")
    print("• 10 Different Voices with audio generation")
    print("• Pexels realistic image style")
    print("• Video with audio, images, and text overlay")
    print("• Multiple languages support")
    print("=" * 50)
    
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)