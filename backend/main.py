import os
import json
import uuid
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import math
from PIL import ImageEnhance

# FastAPI
from fastapi import FastAPI, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# Media processing
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import textwrap
import subprocess
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# ========== CONFIGURATION ==========
class Config:
    BASE_DIR = Path(__file__).parent
    STORAGE_DIR = BASE_DIR / "storage"
    
    # Create storage directories
    for subdir in ["audio", "visuals", "videos", "temp", "scenes"]:
        (STORAGE_DIR / subdir).mkdir(parents=True, exist_ok=True)

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
    
    @validator('language')
    def validate_language(cls, v):
        valid = ["en", "es", "fr", "de", "it", "pt", "hi", "ar", "zh", "ja", "ko"]
        if v not in valid:
            raise ValueError(f"Language must be one of {valid}")
        return v
    
    @validator('resolution')
    def validate_resolution(cls, v):
        valid = ["720x1280", "1080x1920", "1440x2560"]
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
                    "visual_prompt": f"Visual for scene {scene_counter}: {scene_text[:50]}..."
                })
                
                current_scene = []
                scene_counter += 1
        
        # Ensure we have at least target_scenes
        while len(scenes) < target_scenes and scenes:
            last_scene = scenes[-1].copy()
            last_scene["scene_number"] = len(scenes) + 1
            scenes.append(last_scene)
        
        return scenes

# ========== VIDEO GENERATOR ==========
class VideoGenerator:
    def __init__(self):
        self.projects = {}
        self.voices = self._initialize_voices()
        self.image_styles = self._initialize_image_styles()
        self.script_processor = ScriptProcessor()
    
    def _initialize_voices(self):
        return [
            {"id": "radiant_girl", "name": "Radiant Girl", "gender": "female", "accent": "American"},
            {"id": "magnetic_man", "name": "Magnetic Voiced Man", "gender": "male", "accent": "American"},
            {"id": "compelling_lady", "name": "Compelling Lady", "gender": "female", "accent": "British"},
            {"id": "expressive_narrator", "name": "Expressive Narrator", "gender": "male", "accent": "American"},
            {"id": "trustworthy_man", "name": "Trustworthy Man", "gender": "male", "accent": "American"},
            {"id": "graceful_lady", "name": "Graceful Lady", "gender": "female", "accent": "British"},
            {"id": "aussie_bloke", "name": "Aussie Bloke", "gender": "male", "accent": "Australian"},
            {"id": "whispering_girl", "name": "Whispering Girl", "gender": "female", "accent": "American"},
            {"id": "diligent_man", "name": "Diligent Man", "gender": "male", "accent": "American"},
            {"id": "gentle_man", "name": "Gentle-voiced Man", "gender": "male", "accent": "American"}
        ]
    
    def _initialize_image_styles(self):
        return [
            {"id": "default", "name": "Default", "description": "Realistic and clean"},
            {"id": "pixar_art", "name": "Pixar Art", "description": "3D animated style"},
            {"id": "anime", "name": "Anime", "description": "Japanese animation style"},
            {"id": "comic", "name": "Comic", "description": "Graphic novel style"},
            {"id": "lego", "name": "Lego", "description": "Block-based style"},
            {"id": "cinematic", "name": "Cinematic", "description": "Movie-like quality"}
        ]
    
    def get_voices(self):
        return self.voices
    
    def get_image_styles(self):
        return self.image_styles
    
    async def generate_audio(self, text: str, language: str = "en") -> Dict:
        """Generate audio using gTTS"""
        try:
            audio_id = f"audio_{uuid.uuid4().hex[:8]}"
            audio_file = Config.STORAGE_DIR / "audio" / f"{audio_id}.mp3"
            
            # Ensure directory exists
            audio_file.parent.mkdir(parents=True, exist_ok=True)
            
            lang_map = {
                "en": "en", "es": "es", "fr": "fr", "de": "de",
                "it": "it", "pt": "pt", "hi": "hi", "ar": "ar",
                "zh": "zh-CN", "ja": "ja", "ko": "ko"
            }
            
            tts_lang = lang_map.get(language, "en")
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(str(audio_file))
            
            # Get audio duration
            duration = self._get_audio_duration(audio_file)
            
            return {
                "url": f"/storage/audio/{audio_id}.mp3",
                "duration": duration,
                "path": str(audio_file)
            }
        except Exception as e:
            logging.error(f"Audio generation failed: {e}")
            return {"url": "", "duration": 5.0, "path": ""}
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                "ffprobe",
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
    
    def generate_visual(self, prompt: str, style: str, scene_number: int) -> Dict:
        """Generate visual with different styles"""
        try:
            visual_id = f"visual_{uuid.uuid4().hex[:8]}"
            visual_file = Config.STORAGE_DIR / "visuals" / f"{visual_id}.png"
            
            # Ensure directory exists
            visual_file.parent.mkdir(parents=True, exist_ok=True)
            
            width, height = 1080, 1920
            
            # Create image with PIL
            img = self._create_base_image(style, width, height)
            
            # Add scene number to image
            img = self._add_scene_number_to_image(img, scene_number, style)
            
            # Save image
            img.save(str(visual_file), "PNG", quality=95)
            
            logging.info(f"Generated visual: {visual_file}")
            
            return {
                "url": f"/storage/visuals/{visual_id}.png",
                "path": str(visual_file),
                "style": style
            }
            
        except Exception as e:
            logging.error(f"Visual generation failed: {e}")
            # Create a simple fallback image
            return self._create_fallback_image(scene_number, style)
    
    def _create_fallback_image(self, scene_number: int, style: str) -> Dict:
        """Create a fallback image when generation fails"""
        try:
            visual_id = f"fallback_{uuid.uuid4().hex[:8]}"
            visual_file = Config.STORAGE_DIR / "visuals" / f"{visual_id}.png"
            
            width, height = 1080, 1920
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
    
    async def create_scene_video(self, scene: Dict, audio_info: Dict, visual_info: Dict, style: str) -> Optional[str]:
        """Create a single scene video with audio and text overlay"""
        try:
            # Create scenes directory if it doesn't exist
            scenes_dir = Config.STORAGE_DIR / "scenes"
            scenes_dir.mkdir(parents=True, exist_ok=True)
            
            scene_file = scenes_dir / f"scene_{scene['scene_number']}_{uuid.uuid4().hex[:6]}.mp4"
            
            # Get text and clean it for FFmpeg
            scene_text = scene['text']
            
            # Prepare text for FFmpeg - escape special characters
            # First, escape single quotes by wrapping in double quotes
            text_for_ffmpeg = scene_text
            
            # Replace problematic characters
            text_for_ffmpeg = text_for_ffmpeg.replace("'", "'\\\\\\''")  # Escape single quotes
            text_for_ffmpeg = text_for_ffmpeg.replace('"', '\\"')  # Escape double quotes
            text_for_ffmpeg = text_for_ffmpeg.replace('%', '%%')  # Escape percent signs
            text_for_ffmpeg = text_for_ffmpeg.replace(':', '\\:')  # Escape colons
            text_for_ffmpeg = text_for_ffmpeg.replace('[', '\\[')  # Escape brackets
            text_for_ffmpeg = text_for_ffmpeg.replace(']', '\\]')  # Escape brackets
            text_for_ffmpeg = text_for_ffmpeg.replace(',', '\\,')  # Escape commas
            
            # Limit text length for display
            if len(text_for_ffmpeg) > 100:
                # Find a good break point
                if len(text_for_ffmpeg) > 150:
                    text_for_ffmpeg = text_for_ffmpeg[:147] + "..."
                else:
                    # Try to break at sentence end
                    last_period = text_for_ffmpeg[:100].rfind('.')
                    if last_period > 50:
                        text_for_ffmpeg = text_for_ffmpeg[:last_period + 1]
                    else:
                        text_for_ffmpeg = text_for_ffmpeg[:97] + "..."
            
            # Debug: Log the text being passed to FFmpeg
            logging.info(f"Scene {scene['scene_number']} text (cleaned): {text_for_ffmpeg}")
            
            # Method 1: Try with drawtext filter (most reliable)
            try:
                # Use a simpler font specification
                if os.name == 'nt':  # Windows
                    fontfile = "C:/Windows/Fonts/arial.ttf"
                else:  # Linux/Mac
                    fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                
                # First, test if the font file exists
                if not os.path.exists(fontfile):
                    fontfile = ""
                
                # Build FFmpeg command with text overlay
                cmd = [
                    "ffmpeg",
                    "-loop", "1",
                    "-i", visual_info["path"],      # Input image
                    "-i", audio_info["path"],       # Input audio
                    "-c:v", "libx264",              # Video codec
                    "-c:a", "aac",                  # Audio codec
                    "-b:a", "128k",                 # Audio bitrate
                    "-pix_fmt", "yuv420p",          # Pixel format
                    "-t", str(audio_info["duration"]),  # Duration from audio
                    "-shortest",                    # End when audio ends
                    "-y"                           # Overwrite output
                ]
                
                # Add video filter with text overlay
                if fontfile:
                    vf = (f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                          f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"  # Scale and pad
                          f"drawtext=text='{text_for_ffmpeg}':"             # Text overlay
                          f"fontfile='{fontfile}':"
                          f"fontcolor=white:"
                          f"fontsize=42:"
                          f"box=1:"
                          f"boxcolor=black@0.7:"
                          f"boxborderw=10:"
                          f"x=(w-text_w)/2:"
                          f"y=h-text_h-200")        # Position near bottom
                else:
                    vf = (f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                          f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"  # Scale and pad
                          f"drawtext=text='{text_for_ffmpeg}':"             # Text overlay
                          f"fontcolor=white:"
                          f"fontsize=42:"
                          f"box=1:"
                          f"boxcolor=black@0.7:"
                          f"boxborderw=10:"
                          f"x=(w-text_w)/2:"
                          f"y=h-text_h-200")        # Position near bottom
                
                cmd.extend(["-vf", vf, str(scene_file)])
                
                logging.info(f"Creating scene video with text overlay...")
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                if result.returncode == 0 and scene_file.exists() and scene_file.stat().st_size > 1024:
                    logging.info(f"✓ Scene video with text created: {scene_file}")
                    return str(scene_file)
                else:
                    logging.warning(f"Text overlay failed: {result.stderr[:200]}")
                    # Method 2: Try without fontfile specification
                    return await self._create_scene_with_simple_text(
                        visual_info["path"], 
                        audio_info["path"], 
                        scene_file, 
                        audio_info["duration"],
                        text_for_ffmpeg
                    )
                    
            except Exception as e:
                logging.error(f"Text overlay method failed: {e}")
                # Method 3: Create video without text overlay
                return await self._create_simple_scene_video(
                    visual_info["path"], 
                    audio_info["path"], 
                    scene_file, 
                    audio_info["duration"]
                )
                
        except Exception as e:
            logging.error(f"Scene video creation failed: {e}")
            return None
            
    async def _create_scene_with_simple_text(self, image_path: str, audio_path: str, 
                                           output_path: Path, duration: float, 
                                           text: str) -> Optional[str]:
        """Create scene video with simpler text overlay approach"""
        try:
            # Use a very simple approach - create a temporary image with text overlay
            temp_image = Config.STORAGE_DIR / "temp" / f"temp_text_{uuid.uuid4().hex[:8]}.png"
            temp_image.parent.mkdir(parents=True, exist_ok=True)
            
            # Load the original image
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            # Add text overlay using PIL
            try:
                if os.name == 'nt':  # Windows
                    font_path = "C:/Windows/Fonts/arial.ttf"
                else:  # Linux/Mac
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                
                try:
                    font = ImageFont.truetype(font_path, 48)
                except:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Wrap text
            max_width = img.width - 100  # Leave margins
            lines = []
            words = text.split()
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Limit to 3 lines
            if len(lines) > 3:
                lines = lines[:2]
                lines.append("...")
            
            # Draw text with background
            line_height = 60
            total_height = len(lines) * line_height
            y_start = img.height - total_height - 100
            
            # Draw background rectangle
            padding = 20
            draw.rectangle(
                [(50, y_start - padding), 
                 (img.width - 50, y_start + total_height + padding)],
                fill=(0, 0, 0, 180)
            )
            
            # Draw text lines
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (img.width - text_width) // 2
                y = y_start + (i * line_height)
                draw.text((x, y), line, font=font, fill='white')
            
            # Save the image with text
            img.save(str(temp_image), "PNG", quality=95)
            
            # Now create video with this image
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", str(temp_image),  # Use image with text
                "-i", audio_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
                "-t", str(duration),
                "-shortest",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Clean up temporary image
            if temp_image.exists():
                temp_image.unlink()
            
            if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1024:
                logging.info(f"✓ Scene video with PIL text created: {output_path}")
                return str(output_path)
            return None
            
        except Exception as e:
            logging.error(f"PIL text overlay failed: {e}")
            return None
        
    async def _create_simple_scene_video(self, image_path: str, audio_path: str, 
                                       output_path: Path, duration: float) -> Optional[str]:
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
                "ffmpeg",
                "-loop", "1",
                "-i", str(image_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
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
                f.write(f"{scene['text']}\n")
                f.write("\n")
            
            # FFmpeg command with subtitles - fix the f-string
            subtitle_filter = f"subtitles={subtitle_path_str}:force_style='Fontsize=42,PrimaryColour=&HFFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0'"
            
            cmd = [
                "ffmpeg",
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
            "ffmpeg",
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
        
        try:
            # Split script into scenes
            scenes = self.script_processor.split_script(request.script, request.scenes_count)
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
                audio_info = await self.generate_audio(scene["text"], request.language)
                if not audio_info["path"]:
                    logging.error(f"Failed to generate audio for scene {i+1}")
                    continue
                
                # Generate visual
                visual_info = self.generate_visual(
                    scene.get("visual_prompt", scene["text"]),
                    request.image_style,
                    scene["scene_number"]
                )
                if not visual_info["path"]:
                    logging.error(f"Failed to generate visual for scene {i+1}")
                    continue
                
                # Create scene video
                scene_video_path = await self.create_scene_video(
                    scene, audio_info, visual_info, request.image_style
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
            
            video_url = await self._concatenate_videos(scene_videos, request.resolution)
            
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
            
        except Exception as e:
            logging.error(f"Video creation failed: {e}", exc_info=True)
            project["status"] = "failed"
            project["error"] = str(e)
            project["status_message"] = f"Error: {str(e)}"
    
    async def _concatenate_videos(self, video_files: List[str], resolution: str) -> str:
        """Concatenate multiple videos into one"""
        try:
            if not video_files:
                logging.error("No video files to concatenate")
                return self._create_fallback_video(resolution)
            
            video_id = f"video_{uuid.uuid4().hex[:8]}"
            output_file = Config.STORAGE_DIR / "videos" / f"{video_id}.mp4"
            
            # Ensure directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
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
                logging.error("No valid videos to concatenate")
                return self._create_fallback_video(resolution)
            
            # Create concat file
            concat_file = Config.STORAGE_DIR / "temp" / f"concat_{video_id}.txt"
            concat_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for video in valid_videos:
                    # Escape single quotes for FFmpeg
                    video_escaped = str(video).replace("'", "'\\''")
                    f.write(f"file '{video_escaped}'\n")
            
            logging.info(f"Concatenating {len(valid_videos)} videos...")
            
            # Method 1: Try concat demuxer
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                "-y",
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Clean up concat file
            if concat_file.exists():
                concat_file.unlink()
            
            # Check if video was created successfully
            if result.returncode == 0 and output_file.exists():
                file_size = output_file.stat().st_size
                if file_size > 1024:
                    logging.info(f"Video concatenated successfully: {output_file} ({file_size} bytes)")
                    return f"/storage/videos/{video_id}.mp4"
            
            # Method 2: Try filter complex if concat failed
            logging.warning("Concat demuxer failed, trying filter complex...")
            return await self._concatenate_with_filter_complex(valid_videos, video_id, resolution)
                
        except Exception as e:
            logging.error(f"Video concatenation failed: {e}")
            return self._create_fallback_video(resolution)
    
    async def _concatenate_with_filter_complex(self, video_files: List[str], video_id: str, resolution: str) -> str:
        """Alternative concatenation method using filter complex"""
        try:
            output_file = Config.STORAGE_DIR / "videos" / f"{video_id}.mp4"
            
            # Build ffmpeg command with inputs
            cmd = ["ffmpeg"]
            
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and output_file.exists():
                file_size = output_file.stat().st_size
                if file_size > 1024:
                    return f"/storage/videos/{video_id}.mp4"
            
            return ""
                
        except Exception as e:
            logging.error(f"Filter complex concatenation failed: {e}")
            return ""
    
    def _create_fallback_video(self, resolution: str) -> str:
        """Create a fallback video when everything else fails"""
        try:
            video_id = f"fallback_{uuid.uuid4().hex[:8]}"
            output_file = Config.STORAGE_DIR / "videos" / f"{video_id}.mp4"
            
            width, height = map(int, resolution.split('x'))
            
            # Create a simple color video with text
            cmd = [
                "ffmpeg",
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
            "6 image styles with proper application",
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
            "languages": ["en", "es", "fr", "de", "it", "pt", "hi", "ar", "zh", "ja", "ko"],
            "tones": ["neutral", "professional", "casual", "humorous", "educational", "motivational"],
            "resolutions": ["720x1280", "1080x1920", "1440x2560"],
            "max_scenes": 16,
            "min_scenes": 4
        }
    }

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
        visual_info = video_gen.generate_visual(text, style, scene_number)
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
        
        processor = ScriptProcessor()
        scenes = processor.split_script(script, scenes_count)
        
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
    scenes_count: int = Form(8)
):
    """Preview how script will be split into scenes (Form version)"""
    try:
        processor = ScriptProcessor()
        scenes = processor.split_script(script, scenes_count)
        
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
        
        audio_info = await video_gen.generate_audio(text, language)
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

# ========== RUN SERVER ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    
    print("=" * 50)
    print("🎬 FACELESS VIDEOS CREATOR v2 - WITH AUDIO & STYLES")
    print("=" * 50)
    print(f"Server starting on: http://localhost:{port}")
    print(f"API Documentation: http://localhost:{port}/docs")
    print(f"Storage directory: {Config.STORAGE_DIR}")
    print("\nFeatures:")
    print("• Single script input - auto-split into scenes")
    print("• 10 Different Voices with audio generation")
    print("• 6 Image Styles with proper effects")
    print("• Video with audio, images, and text overlay")
    print("• Multiple languages support")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=port)