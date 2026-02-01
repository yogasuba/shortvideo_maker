
import os
import subprocess
import uuid
from pathlib import Path
import unicodedata

# Text from user screenshot
text = "ராமமேஸ்வரம் பபோலவே, திலதர்ப்பணபுரி பூஜைகளுக்கும் பிரசித்தி பெறுகிறது."

# Try NFC Normalization
text_nfc = unicodedata.normalize('NFC', text)

def create_video(font_name, normalized_text, suffix):
    output_dir = Path("test_shaping")
    output_dir.mkdir(exist_ok=True)
    
    ass_file = output_dir / f"test_{suffix}.ass"
    video_file = output_dir / f"test_{suffix}.mp4"
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3.5,0.5,2,50,50,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{normalized_text}
"""
    
    with open(ass_file, "w", encoding="utf-8-sig") as f:
        f.write(header)
    
    # Use relative path for subtitles
    rel_ass = os.path.relpath(ass_file, Path.cwd()).replace("\\", "/")
    
    cmd = [
        "C:/ffmpeg/bin/ffmpeg.exe",
        "-f", "lavfi",
        "-i", "color=c=black:s=1080x1920:d=5",
        "-vf", f"subtitles={rel_ass}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y",
        str(video_file)
    ]
    
    print(f"Testing {font_name} with {suffix}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Created {video_file}")
    else:
        # Try with fontsdir if first attempt fails
        cmd[6] = f"subtitles={rel_ass}:fontsdir=C\\\\:/Windows/Fonts"
        result2 = subprocess.run(cmd, capture_output=True, text=True)
        if result2.returncode == 0:
            print(f"✓ Created {video_file} (with fontsdir)")
        else:
            print(f"✗ Failed {suffix}")
            print(f"Error: {result2.stderr[-300:]}")

# Test variants
create_video("Nirmala UI", text, "raw")
create_video("Nirmala UI", text_nfc, "nfc")
create_video("Arial", text_nfc, "arial")
