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

# Complex script rendering
from complex_script_renderer import ComplexScriptRenderer
from font_downloader import ensure_fonts_available
from ffmpeg_downloader import ensure_ffmpeg_has_harfbuzz
from exceptions import (
    VideoPipelineError, UserInputError, ResourceMissingError, 
    FFmpegError, TimeOutError, StorageError, AssetDownloadError,
    VideoConcatenationError
)

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
    
    # Create storage directories
    for subdir in ["audio", "visuals", "videos", "temp", "scenes"]:
        (STORAGE_DIR / subdir).mkdir(parents=True, exist_ok=True)
    
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
                
                scenes.append({
                    "scene_number": scene_counter,
                    "text": scene_text,
                    "duration": 5,
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
                logging.info("DEBUG: Attempting OpenAI Direct...")
                client = AsyncOpenAI(api_key=openai_key)
                # Use GPT-4o if possible, fallback to gpt-3.5-turbo
                for model in ["gpt-4o", "gpt-3.5-turbo"]:
                    voice_overs = await generate_with_client(client, model, system_prompt, user_prompt)
                    if voice_overs:
                        logging.info(f"✓ Success with OpenAI Direct model: {model}")
                        break
            except Exception as e:
                logging.error(f"OpenAI Direct setup failed: {e}")

        # 2. Try OpenRouter (if OpenAI failed or key missing)
        if not voice_overs:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            # Only try OpenRouter if it's NOT an OpenAI key used mistakenly as OpenRouter key
            if openrouter_key and not (openrouter_key.startswith("sk-proj-") or openrouter_key.startswith("sk-")):
                try:
                    logging.info("DEBUG: Attempting OpenRouter...")
                    client = AsyncOpenAI(
                        api_key=openrouter_key,
                        base_url="https://openrouter.ai/api/v1"
                    )
                    # Try a few reliable FREE models on OpenRouter
                    models = [
                        "google/gemini-2.0-flash-exp:free",
                        "google/gemini-2.0-flash-thinking-exp:free",
                        "mistralai/pixtral-12b:free",
                        "qwen/qwen-2-7b-instruct:free",
                        "openai/gpt-3.5-turbo"
                    ]
                    
                    for model in models:
                        voice_overs = await generate_with_client(client, model, system_prompt, user_prompt)
                        if voice_overs:
                            logging.info(f"✓ Success with OpenRouter model: {model}")
                            break
                except Exception as e:
                    logging.error(f"OpenRouter setup failed: {e}")

        # Apply results or fallback
        if voice_overs:
            logging.info("DEBUG: Applying generated voice-overs.")
            for i, scene in enumerate(scenes):
                # Safety check for duplicates
                if voice_overs[i].strip().lower() == scene["text"].strip().lower():
                    logging.warning(f"Scene {i+1} voice-over identical to text. AI ignored instructions.")
                
                scene["voice_over"] = voice_overs[i]
        else:
            logging.warning("ALL AI GENERATION FAILED. Falling back to using scene description as voice-over.")
            for scene in scenes:
                scene["voice_over"] = scene["text"]
        return scenes


# ========== VIDEO GENERATOR ==========
class VideoGenerator:
    def __init__(self):
        self.projects = {}
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

            audio_id = f"audio_{uuid.uuid4().hex[:8]}"
            audio_file = Config.STORAGE_DIR / "audio" / f"{audio_id}.mp3"
            audio_file.parent.mkdir(parents=True, exist_ok=True)

            # Find the correct voice id or default to Rachel
            voice = voice_id if voice_id else "21m00Tcm4TlvDq8ikWAM"
            
            logging.info(f"Generating ElevenLabs audio for voice {voice}...")
            
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
                return {
                    "url": f"/storage/audio/{audio_id}.mp3",
                    "duration": duration,
                    "path": str(audio_file)
                }
            
            return {"url": "", "duration": 5.0, "path": ""}

        except Exception as e:
            logging.error(f"ElevenLabs audio generation error: {e}")
            return {"url": "", "duration": 5.0, "path": ""}
    
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
                return {
                    "url": f"/storage/visuals/{visual_id}.png",
                    "path": str(visual_file),
                    "style": "custom"
                }

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
                            return {
                                "url": f"/storage/visuals/{visual_id}.png",
                                "path": str(visual_file),
                                "style": style
                            }
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
                            return {
                                "url": f"/storage/visuals/{visual_id}.png",
                                "path": str(visual_file),
                                "style": style
                            }
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
                        return {
                            "url": f"/storage/visuals/{visual_id}.png",
                            "path": str(visual_file),
                            "style": style
                        }
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
                        return {
                            "url": f"/storage/visuals/{visual_id}.png",
                            "path": str(visual_file),
                            "style": style
                        }
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
                            return {
                                "url": f"/storage/visuals/{visual_id}.png",
                                "path": str(visual_file),
                                "style": style
                            }
                except Exception as pe:
                    logging.warning(f"Pexels search failed: {pe}")

            # 6. Last Fallback: PIL Gradient
            logging.info(f"Falling back to PIL generation for scene {scene_number}")
            img = self._create_base_image(style, width, height)
            img = self._add_scene_number_to_image(img, scene_number, style)
            img.save(str(visual_file), "PNG", quality=95)
            
            return {
                "url": f"/storage/visuals/{visual_id}.png",
                "path": str(visual_file),
                "style": style
            }
            
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
            # Subtitle should be narration.
            subtitle_text = scene.get('voice_over', scene.get('text', ''))
            
            scene_path = await self._create_scene_with_simple_text(
                visual_info["path"], 
                audio_info["path"], 
                scene_file, 
                audio_info["duration"],
                subtitle_text,
                resolution,
                language,
                subtitle_style=subtitle_style
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
                                           subtitle_style: str = "static") -> Optional[str]:
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
                    image_path, audio_path, output_path, duration, text, resolution, language
                )
            
            # === COMPLEX SCRIPT PIPELINE (ASS/LIBASS) ===
            logging.info(f"Entering Complex Script Pipeline (LIBASS) for {language}")
            
            # 1. Find Font
            font_path = renderer.find_font(language)
            if not font_path:
                msg = f"CRITICAL: No font found for {language}. Cannot generate subtitles."
                logging.error(msg)
                raise RuntimeError(msg)
            
            # 2. Wrap Text
            max_width_lines = 3000  # Set high to let Libass handle accurate wrapping via margins
            font_size = 60  # Increased font size for readability
            
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
                wrapped_text,
                ass_file_path,
                font_path,
                font_size,
                duration,
                resolution,
                language,
                margin_v=margin_v,
                style=subtitle_style
            )
            
            # 4. Generate Clean Video (Image + Audio) - Intermediate
            temp_video = Config.STORAGE_DIR / "temp" / f"raw_{uuid.uuid4().hex}.mp4"
            width, height = resolution.split('x')
            
            # Create base video first
            cmd_base = [
                Config.get_ffmpeg(),
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
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
                                            text: str, resolution: str = "1080x1920", language: str = "en") -> Optional[str]:
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
            
            # Draw text with background
            bbox_sample = draw.textbbox((0, 0), "Ayg", font=font)
            line_height = (bbox_sample[3] - bbox_sample[1]) + 15
            total_height = len(lines) * line_height
            
            y_start = img.height - total_height - (img.height * 0.15)
            
            # Draw semi-transparent background
            padding = 15
            box_fill = (0, 0, 0, 160)
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            for i, line in enumerate(lines):
                line_bbox = overlay_draw.textbbox((0, 0), line, font=font)
                line_w = line_bbox[2] - line_bbox[0]
                line_h = line_bbox[3] - line_bbox[1]
                lx = (img.width - line_w) // 2
                ly = y_start + (i * line_height)
                
                overlay_draw.rectangle(
                    [(lx - padding, ly - 5), 
                     (lx + line_w + padding, ly + line_h + 10)],
                    fill=box_fill
                )
            
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Draw each line centered
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = (img.width - w) // 2
                y = y_start + (i * line_height)
                draw.text((x, y), line, font=font, fill='white')
            
            img.save(str(temp_image), "PNG", quality=95)
            
            # Now create video with this image
            cmd = [
                Config.get_ffmpeg(),
                "-loop", "1",
                "-i", str(temp_image),
                "-i", audio_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={resolution.replace('x', ':')}:force_original_aspect_ratio=decrease,pad={resolution.replace('x', ':')}:(ow-iw)/2:(oh-ih)/2:color=black",
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
                "-i", str(image_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
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
                # Use voice_over if available, otherwise fallback to text
                voice_text = scene.get("voice_over", scene["text"])
                audio_info = await self.generate_audio(voice_text, request.language, request.voice)
                if not audio_info["path"]:
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
            
            video_url = await self._concatenate_videos(scene_videos, request.resolution, use_demuxer=use_demuxer)
            
            # Update project
            project["progress"] = 100
            project["status"] = "completed" if video_url else "failed"
            project["video_url"] = video_url
            project["completed_at"] = datetime.now().isoformat()
            
            if video_url:
                video_path = Config.STORAGE_DIR / video_url.replace('/storage/', '')
                if video_path.exists():
                    file_size = video_path.stat().st_size
                    project["status_message"] = f"Video created successfully ({file_size/1024/1024:.1f} MB)"
                    logging.info(f"Final video created: {video_path} ({file_size} bytes)")
                else:
                    project["status_message"] = "Video created but file not found"
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
                logging.info(f"Using Concat Demuxer (Preferred) for {len(valid_videos)} videos...")
                try:
                    return await self._concatenate_with_demuxer(valid_videos, video_id)
                except Exception as e:
                    logging.warning(f"Concat demuxer failed: {e}. Falling back to filter complex...")
                    return await self._concatenate_with_filter_complex(valid_videos, video_id, resolution)
            else:
                logging.info(f"Using Filter Complex (Standard) for {len(valid_videos)} videos...")
                try:
                    return await self._concatenate_with_filter_complex(valid_videos, video_id, resolution)
                except Exception as e:
                    logging.warning(f"Filter complex failed (likely code 4294967274). Error: {e}")
                    logging.info("Falling back to Concat Demuxer...")
                    return await self._concatenate_with_demuxer(valid_videos, video_id)
                
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
                    return f"/storage/videos/{video_id}.mp4"
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
            
            # Build filter complex
            filter_parts = []
            for i in range(len(video_files)):
                filter_parts.append(f"[{i}:v]")
                filter_parts.append(f"[{i}:a]")
            
            filter_complex = "".join(filter_parts) + f"concat=n={len(video_files)}:v=1:a=1[outv][outa]"
            
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-c:a", "aac",
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
                    return f"/storage/videos/{video_id}.mp4"
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
    """Create a video from script"""
    try:
        # Validate voice exists
        valid_voices = [v["id"] for v in video_gen.get_voices()]
        if request.voice not in valid_voices:
            raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {valid_voices}")
        
        # Validate image style exists
        valid_styles = [s["id"] for s in video_gen.get_image_styles()]
        if request.image_style not in valid_styles:
            raise HTTPException(status_code=400, detail=f"Invalid image style. Must be one of: {valid_styles}")
        
        project_id = f"project_{uuid.uuid4().hex[:8]}"
        
        # Store project
        video_gen.projects[project_id] = {
            "project_id": project_id,
            "title": request.title,
            "status": "processing",
            "progress": 0,
            "status_message": "Starting video creation...",
            "created_at": datetime.now().isoformat(),
            "video_url": None,
            "error": None,
            "script": request.script[:200] + "..." if len(request.script) > 200 else request.script,
            "voice": request.voice,
            "image_style": request.image_style
        }
        video_gen.save_projects()
        
        # Start processing in background
        background_tasks.add_task(video_gen.create_video, project_id, request)
        
        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "status": "processing",
                "check_status": f"/api/projects/{project_id}/status"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """Get project status"""
    project = video_gen.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "success": True,
        "data": project
    }

# Update the preview endpoints to return proper data
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
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        video_path,
        filename=video_filename,
        media_type='video/mp4'
    )

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
        
        return {
            "success": True,
            "data": {
                "url": f"/storage/visuals/{filename}",
                "path": str(file_path)
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
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
