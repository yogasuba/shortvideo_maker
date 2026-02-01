
import asyncio
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import logging
import unicodedata
import subprocess

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VideoGenerator, Config

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def test_tamil_ass_pipeline():
    print("--- Starting Tamil ASS Pipeline verification ---")
    vg = VideoGenerator()
    
    # Create test storage
    Config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (Config.STORAGE_DIR / "temp").mkdir(parents=True, exist_ok=True)
    (Config.STORAGE_DIR / "scenes").mkdir(parents=True, exist_ok=True)
    
    # 1. Create a dummy image
    img_path = Config.STORAGE_DIR / "test_tamil_bg.png"
    img = Image.new('RGB', (1080, 1920), color='#1e1e2e')
    ImageDraw.Draw(img).rectangle([(100, 100), (980, 900)], fill='#313244')
    img.save(img_path)
    print(f"✓ Created test background: {img_path}")
    
    # 2. Generate a valid silent audio file using FFmpeg
    audio_path = Config.STORAGE_DIR / "test_tamil_audio.mp3"
    print("Generating silent audio for testing...")
    subprocess.run([
        Config.get_ffmpeg(), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
        "-t", "5", "-q:a", "9", "-y", str(audio_path)
    ], check=True, capture_output=True)
    print(f"✓ Created dummy audio: {audio_path}")
    
    # 3. Tamil Text
    # "Hello World" in Tamil: வணக்கம் உலகு
    # Complex combination: ரு + ூ = ரூ (Requires shaping)
    tamil_text = "வணக்கம் உலகு. தமிழ் வாழ்க. ரு + ூ = ரூ."
    
    output_path = Config.STORAGE_DIR / "test_tamil_output.mp4"
    if output_path.exists():
        output_path.unlink()
    
    print(f"--- Testing Rendering of: {tamil_text} ---")
    
    # Call the private method that now contains the ASS logic
    result = await vg._create_scene_with_simple_text(
        str(img_path), 
        str(audio_path), 
        output_path, 
        duration=5.0, 
        text=tamil_text, 
        resolution="1080x1920",
        language="ta"
    )
    
    if result:
        print(f"\nSUCCESS: Video generated at {result}")
        print("Please check this video to ensure text is rendered correctly (no boxes or dotted circles).")
        
        # --- Concatenation Verification ---
        print("\n--- Verifying Concatenation Fix (Demuxer) ---")
        try:
            # Create a duplicate for concatenation
            scene2 = output_path.parent / "test_scene_2.mp4"
            import shutil
            shutil.copy(output_path, scene2)
            print(f"Created duplicate scene: {scene2}")
            
            # Test concatenation with demuxer
            # We call the method we added to VideoGenerator
            print("Running _concatenate_with_demuxer...")
            final_video = await vg._concatenate_with_demuxer([str(output_path), str(scene2)], "test_concat_id")
            
            if final_video and (Config.STORAGE_DIR / "videos" / "test_concat_id.mp4").exists():
                print(f"SUCCESS: Concatenation successful! Final video: {final_video}")
            else:
                print("FAILURE: Concatenation returned empty or file missing")
                raise Exception("Concatenation failed")
                
        except Exception as e:
            print(f"FAILURE: Concatenation threw exception: {e}")
            raise e
            
    else:
        print("\nFAILURE: Video generation returned None.")

if __name__ == "__main__":
    try:
        asyncio.run(test_tamil_ass_pipeline())
        with open("verification_result.txt", "w") as f:
            f.write("SUCCESS")
    except Exception as e:
        import traceback
        with open("verification_result.txt", "w") as f:
            f.write(f"FAILURE\n{e}\n{traceback.format_exc()}")
        print(f"Test failed with exception: {e}")
        traceback.print_exc()
