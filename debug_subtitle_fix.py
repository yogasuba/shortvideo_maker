
import asyncio
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from main import VideoGenerator, Config

async def test_subtitle_fix():
    print("Initializing...")
    vg = VideoGenerator()
    
    # 1. Create a dummy image (Landscape to force letterboxing)
    # 16:9 Landscape (1920x1080) in a 9:16 Portrait Video (1080x1920)
    # This creates large black bars. We want Top Alignment.
    img_path = Config.STORAGE_DIR / "test_landscape.png"
    img = Image.new('RGB', (1920, 1080), color='#2E86C1') # Nice Blue
    d = ImageDraw.Draw(img)
    d.text((100, 100), "TOP LEFT", fill="white")
    d.text((100, 900), "BOTTOM LEFT", fill="white")
    img.save(img_path)
    
    # Dummy audio
    audio_path = Config.STORAGE_DIR / "dummy_audio.mp3"
    if not audio_path.exists():
        with open(audio_path, 'wb') as f: f.write(b'\0'*1024)

    output_path = Config.STORAGE_DIR / "verify_subtitle_fix.mp4"
    if output_path.exists(): output_path.unlink()
    
    # Tamil Text
    text = "இது ஒரு நீண்ட தமிழ் வசனம் ஆகும்."
    
    print("Generating video...")
    try:
        # Pass language='ta' to trigger ComplexScriptRenderer
        result = await vg._create_scene_with_simple_text(
            str(img_path),
            str(audio_path),
            output_path,
            5.0,
            text,
            "1080x1920",
            language="ta"
        )
        
        if result:
            print(f"✓ Video generated: {result}")
            print("VERIFY VISUALLY:")
            print("1. Blue image is at the TOP.")
            print("2. Subtitles are inside the blue image at the bottom.")
            print("3. Subtitles have a semi-transparent black background BOX.")
            print("4. Text is larger than before.")
        else:
            print("✗ Check logs for failure.")
            
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'details'): print(e.details)
        if hasattr(e, 'stderr'): print(e.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_subtitle_fix())
