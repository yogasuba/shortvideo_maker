
import asyncio
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import uuid
import logging

# Mock Config
class Config:
    STORAGE_DIR = Path("./test_storage")
    @staticmethod
    def get_ffmpeg():
        return "ffmpeg"

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VideoGenerator

async def test_rendering():
    vg = VideoGenerator()
    
    # Create test storage
    Config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (Config.STORAGE_DIR / "temp").mkdir(parents=True, exist_ok=True)
    (Config.STORAGE_DIR / "scenes").mkdir(parents=True, exist_ok=True)
    
    # Create a dummy image
    img_path = Config.STORAGE_DIR / "dummy.png"
    img = Image.new('RGB', (1080, 1920), color='blue')
    img.save(img_path)
    
    # Long text
    long_text = "This is a very long narration that should definitely trigger the dynamic font sizing logic. It needs to wrap multiple times and the font should shrink until everything fits comfortably on the screen without being cut off or hidden. We want to make sure that even if the narrator talks a lot, the audience can still read every single word in the subtitles."
    
    output_path = Config.STORAGE_DIR / "test_output.mp4"
    audio_path = Config.STORAGE_DIR / "dummy.mp3" # Doesn't need to exist for image generation check
    
    print("Testing rendering...")
    # We call the private method for testing
    result = await vg._create_scene_with_simple_text(
        str(img_path), 
        str(audio_path), 
        output_path, 
        5.0, 
        long_text, 
        "1080x1920"
    )
    
    # Check if temp image exists (we need to catch it before it's deleted)
    # Actually, I'll modify the test to NOT delete the temp image for inspection
    print(f"Result: {result}")
    print("Check test_storage/temp/ for the generated image (if you can find it before it's deleted, or I can modify main.py temporarily)")

if __name__ == "__main__":
    asyncio.run(test_rendering())
