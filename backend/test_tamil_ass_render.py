
import asyncio
import os
import uuid
from pathlib import Path
import subprocess

# Mock Config
class Config:
    BASE_DIR = Path(__file__).parent
    STORAGE_DIR = BASE_DIR / "test_storage"
    FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"
    
    @classmethod
    def get_ffmpeg(cls):
        return cls.FFMPEG_PATH if os.path.exists(cls.FFMPEG_PATH) else "ffmpeg"

Config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(Config.STORAGE_DIR / "temp").mkdir(parents=True, exist_ok=True)
(Config.STORAGE_DIR / "scenes").mkdir(parents=True, exist_ok=True)

async def test_ass_generation():
    print("Testing ASS Generation...")
    
    scene_number = 1
    text = "இறைவன் முக்தீஸ்வரர் அருள் புரியட்டும்"  # "May Lord Muktheeswarar bless"
    duration = 5.0
    
    ass_file = Config.STORAGE_DIR / "temp" / f"test_scene_{scene_number}.ass"
    
    # 1. Generate ASS Content
    font_name = "Nirmala UI" if os.path.exists("C:/Windows/Fonts/Nirmala.ttc") else "Arial"
    print(f"Using font: {font_name}")
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,50,50,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogue = f"Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{text}\n"
    
    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(dialogue)
        
    print(f"Created ASS file at {ass_file}")
    
    # Verify Content
    with open(ass_file, "r", encoding="utf-8") as f:
        content = f.read()
        if text in content:
            print("✓ Text preserved correctly in ASS file")
        else:
            print("✗ Text corrupted in ASS file")
            
    # 2. Render Video
    output_video = Config.STORAGE_DIR / "scenes" / "test_tamil_render.mp4"
    
    # Create dummy video input (color)
    # Use relative path as implemented in main.py
    try:
        rel_ass_path = os.path.relpath(ass_file, Path.cwd()).replace('\\', '/')
        ass_path_str = rel_ass_path
        print(f"Using relative path: {ass_path_str}")
    except:
        ass_path_str = str(ass_file).replace('\\', '/').replace(':', '\\\\:')

    cmd = [
        Config.get_ffmpeg(),
        "-f", "lavfi",
        "-i", "color=c=black:s=1080x1920:d=5",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", f"subtitles={ass_path_str}",
        "-t", "5",
        "-y",
        str(output_video)
    ]
    
    print("Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0 and output_video.exists():
        print(f"✓ Video rendered successfully: {output_video}")
    else:
        print(f"✗ FFmpeg failed: {result.stderr}")

if __name__ == "__main__":
    asyncio.run(test_ass_generation())
