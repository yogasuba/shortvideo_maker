#!/usr/bin/env python3
"""Test FFmpeg drawtext without text_shaping parameter"""

import subprocess
import tempfile
from pathlib import Path
from PIL import Image
import unicodedata

# Create temp directory
tmpdir = Path(tempfile.gettempdir())

# Create test image
test_img = tmpdir / 'test_tamil_base.png'
img = Image.new('RGB', (1080, 1920), color='#1a1a2e')
img.save(str(test_img))
print(f"Created test image: {test_img}")

# Create silent audio
test_audio = tmpdir / 'test_tamil_audio.mp3'
print("Creating test audio...")
subprocess.run([
    'C:/ffmpeg/bin/ffmpeg.exe',
    '-f', 'lavfi',
    '-i', 'anullsrc=r=44100:cl=mono',
    '-t', '2',
    '-q:a', '9',
    '-acodec', 'libmp3lame',
    '-y',
    str(test_audio)
], capture_output=True, timeout=10)

# Get Tamil font from Windows
tamil_font = 'C:/Windows/Fonts/nirmala.ttc'

# Test text
test_text = 'சாதி மத பாகுபாடின்றி'
test_text = unicodedata.normalize('NFC', test_text)
print(f"Test text: {test_text}")

# Escape for FFmpeg - be very careful with escaping
# Replace: \ -> \\, ' -> '\''
escaped_text = test_text.replace('\\', '\\\\').replace("'", "'\\''")

# Test 1: WITHOUT text_shaping parameter
print("\n=== Test 1: WITHOUT text_shaping parameter ===")
drawtext_filter_no_shaping = (
    f"drawtext="
    f"text='{escaped_text}':"
    f"fontfile='{tamil_font}':"
    f"fontsize=42:"
    f"fontcolor=white:"
    f"x=(w-text_w)/2:"
    f"y=h-text_h-100"
)

cmd = [
    'C:/ffmpeg/bin/ffmpeg.exe',
    '-loop', '1',
    '-i', str(test_img),
    '-i', str(test_audio),
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-c:a', 'aac',
    '-b:a', '128k',
    '-pix_fmt', 'yuv420p',
    '-vf', f'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,{drawtext_filter_no_shaping}',
    '-t', '1',
    '-y',
    str(tmpdir / 'test_output_no_shaping.mp4')
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
print(f"Return code: {result.returncode}")
if result.returncode == 0:
    print("✓ SUCCESS without text_shaping parameter!")
else:
    print(f"✗ Failed")
    if "text_shaping" in result.stderr.lower():
        print("  Error mentions text_shaping")
    print(f"  Error: {result.stderr[-300:]}")

# Test 2: WITH text_shaping parameter
print("\n=== Test 2: WITH text_shaping=1 parameter ===")
drawtext_filter_with_shaping = (
    f"drawtext="
    f"text='{escaped_text}':"
    f"fontfile='{tamil_font}':"
    f"fontsize=42:"
    f"fontcolor=white:"
    f"x=(w-text_w)/2:"
    f"y=h-text_h-100:"
    f"text_shaping=1"
)

cmd[cmd.index('-vf') + 1] = f'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,{drawtext_filter_with_shaping}'
cmd[-1] = str(tmpdir / 'test_output_with_shaping.mp4')

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
print(f"Return code: {result.returncode}")
if result.returncode == 0:
    print("✓ SUCCESS with text_shaping=1 parameter!")
else:
    print(f"✗ Failed")
    if "text_shaping" in result.stderr.lower():
        print("  Error mentions text_shaping - parameter not supported")
    print(f"  Error: {result.stderr[-500:]}")
