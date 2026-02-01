
import os
import subprocess
from pathlib import Path
import unicodedata

# CORRECT Tamil spelling
# 1. Rameswaram: ராமேஸ்வரம் (Ra - me - swa - ra - m)
# 2. Like/As: போலவே (Po - la - ve)
correct_text = "ராமேஸ்வரம் போலவே, திலதர்ப்பணபுரி பூஜைகளுக்கும் பிரசித்தி பெற்றது."

# Decomposed version for comparison
decomposed_text = "".join(unicodedata.normalize('NFD', correct_text))
# Recomposed version (NFC)
nfc_text = unicodedata.normalize('NFC', correct_text)

def test_render(text_to_render, font_name, suffix):
    output_dir = Path("test_tamil_quality")
    output_dir.mkdir(exist_ok=True)
    
    ass_file = output_dir / f"test_{suffix}.ass"
    video_file = output_dir / f"test_{suffix}.mp4"
    frame_file = output_dir / f"frame_{suffix}.png"
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},65,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3.5,0.5,2,50,50,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{text_to_render}
"""
    
    with open(ass_file, "w", encoding="utf-8-sig") as f:
        f.write(header)
    
    rel_ass = os.path.relpath(ass_file, Path.cwd()).replace("\\", "/")
    
    cmd = [
        "C:/ffmpeg/bin/ffmpeg.exe",
        "-f", "lavfi",
        "-i", "color=c=black:s=1080x1920:d=5",
        "-vf", f"subtitles={rel_ass}:fontsdir=C\\\\:/Windows/Fonts",
        "-c:v", "libx264",
        "-t", "1",
        "-y",
        str(video_file)
    ]
    
    subprocess.run(cmd, capture_output=True)
    
    # Extract frame
    extract_cmd = [
        "C:/ffmpeg/bin/ffmpeg.exe",
        "-i", str(video_file),
        "-vframes", "1",
        "-y",
        str(frame_file)
    ]
    subprocess.run(extract_cmd, capture_output=True)
    print(f"Created {frame_file}")

test_render(correct_text, "Nirmala UI", "correct_nirmala")
test_render(nfc_text, "Nirmala UI", "nfc_nirmala")
test_render(correct_text, "Arial", "correct_arial")
