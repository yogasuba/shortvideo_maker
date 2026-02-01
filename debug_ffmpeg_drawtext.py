#!/usr/bin/env python3
"""Debug FFmpeg drawtext with Tamil text"""

import subprocess
from pathlib import Path
from PIL import Image
import unicodedata
from backend.complex_script_renderer import ComplexScriptRenderer

# Create test image
test_img = Path('test_tamil_base.png')
img = Image.new('RGB', (1080, 1920), color='#1a1a2e')
img.save(str(test_img))
print(f"Created test image: {test_img}")

# Create silent audio
test_audio = Path('test_tamil_audio.mp3')
print("Creating test audio...")
result = subprocess.run([
    'C:/ffmpeg/bin/ffmpeg.exe',
    '-f', 'lavfi',
    '-i', 'anullsrc=r=44100:cl=mono',
    '-t', '2',
    '-q:a', '9',
    '-acodec', 'libmp3lame',
    '-y',
    str(test_audio)
], capture_output=True, timeout=10)
print(f"Audio creation return code: {result.returncode}")

# Get Tamil font
renderer = ComplexScriptRenderer()
tamil_font = renderer.find_font('ta')
print(f"Tamil font: {tamil_font}")

# Test text
test_text = 'சாதி மத பாகுபாடின்றி'
test_text = unicodedata.normalize('NFC', test_text)
print(f"Test text: {test_text}")

# Escape for FFmpeg
escaped_text = test_text.replace('\\', '\\\\').replace("'", "'\\''").replace(':', r'\:')
print(f"Escaped text: {escaped_text}")

# Build drawtext filter
drawtext_filter = (
    f"drawtext="
    f"text='{escaped_text}':"
    f"fontfile='{tamil_font.replace(chr(92), '/')}' :"
    f"fontsize=42:"
    f"fontcolor=white:"
    f"x=(w-text_w)/2:"
    f"y=h-text_h-100:"
    f"text_shaping=1"
)

print(f"\nDrawtext filter:\n{drawtext_filter}\n")

# Build full command
cmd = [
    'C:/ffmpeg/bin/ffmpeg.exe',
    '-loop', '1',
    '-i', str(test_img),
    '-i', str(test_audio),
    '-c:v', 'libx264',
    '-c:a', 'aac',
    '-b:a', '128k',
    '-pix_fmt', 'yuv420p',
    '-vf', f'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,{drawtext_filter}',
    '-t', '2',
    '-y',
    'test_output.mp4'
]

print("Running FFmpeg drawtext...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='ignore')

print(f"\nReturn code: {result.returncode}")

if result.returncode != 0:
    print("\n=== STDERR (last 1500 chars) ===")
    print(result.stderr[-1500:] if len(result.stderr) > 1500 else result.stderr)
    print("\n=== STDOUT (last 500 chars) ===")
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
else:
    print("\n✓ FFmpeg drawtext succeeded!")
    output_file = Path('test_output.mp4')
    if output_file.exists():
        print(f"✓ Output file created: {output_file.stat().st_size} bytes")
