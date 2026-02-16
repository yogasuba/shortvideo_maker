import asyncio
import os
import json
from pathlib import Path
import logging
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VideoGenerator, VideoCreateRequest, Config
from complex_script_renderer import ComplexScriptRenderer

logging.basicConfig(level=logging.INFO)

async def test_enhanced_controls():
    print("Testing Enhanced Scene Controls & Subtitle Styles...")
    gen = VideoGenerator()
    
    # Mock scene data
    scene = {
        "scene_number": 1,
        "text": "This is a test scene with enhanced controls.",
        "voice_over": "This is the narration for the test scene.",
        "duration": 8.0,
        "subtitle_position": "center",
        "subtitle_size": 80,
        "subtitle_color": "yellow",
        "subtitle_bg_visible": False,
        "rotation": 90
    }
    
    # 1. Test Silent Audio Creation
    print("\n1. Testing _create_silent_audio...")
    audio_info = await gen._create_silent_audio(5.0)
    print(f"Silent audio info: {audio_info}")
    if audio_info["path"] and os.path.exists(audio_info["path"]):
        print("✓ Silent audio created successfully")
    else:
        print("✗ Silent audio creation failed")

    # 2. Test ASS Generation with Center Alignment, Yellow Color, No BG
    print("\n2. Testing ASS generation with center alignment and custom styling...")
    ass_path = Config.STORAGE_DIR / "temp" / "test_styled.ass"
    font_path = gen.complex_script_renderer.find_font("en")
    ComplexScriptRenderer.generate_ass_file(
        "Styled Aligned Text",
        ass_path,
        font_path,
        font_size=80,
        duration=5.0,
        resolution="1080x1920",
        language="en",
        margin_v=960, # Center of 1920
        style="center",
        color="yellow",
        bg_visible=False
    )
    
    with open(ass_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "Alignment, MarginL, MarginR, MarginV, Encoding" in content:
            # Check if alignment 5 is present in the style line
            lines = content.split('\n')
            style_line = [l for l in lines if l.startswith("Style: Default")][0]
            if ",5," in style_line:
                print("✓ ASS alignment 5 (center) correctly set")
            else:
                 print(f"✗ ASS alignment 5 not found in: {style_line}")
            
            # Check for yellow color (&H0000FFFF)
            if "&H0000FFFF" in style_line:
                print("✓ ASS yellow color correctly set")
            else:
                print(f"✗ ASS yellow color NOT found in: {style_line}")

            # Check for BorderStyle=1 (No box)
            if ",1,1,1,5," in style_line: # BorderStyle=1, Outline=1, Shadow=1, Alignment=5
                print("✓ ASS border style 1 (No box) correctly set")
            else:
                print(f"✗ ASS expected border style 1 (No box) NOT found in: {style_line}")

    # 3. Test Multi-line Text Wrapping
    print("\n3. Testing multi-line text wrapping with explicit newlines...")
    multi_line_text = "Line 1\nLine 2 with some long text to force wrapping if necessary.\nLine 3"
    lines = ComplexScriptRenderer.wrap_text_at_word_boundaries(
        multi_line_text,
        max_width_pixels=500, # Narrow width
        font_path=font_path,
        font_size=60
    )
    print(f"Wrapped lines: {lines}")
    if "Line 1" in lines[0] and "Line 3" in lines[-1]:
        print("✓ Explicit newlines preserved in wrapping")
    else:
        print("✗ Explicit newlines NOT preserved")

    print("\nVerification Complete!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_controls())
