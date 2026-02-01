
import asyncio
import os
from pathlib import Path
import logging
from main import VideoGenerator, Config

# Setup logging
logging.basicConfig(level=logging.INFO)

async def verify_tamil_rendering():
    print("Starting Tamil Subtitle Rendering Verification...")
    
    # Initialize Generator
    gen = VideoGenerator()
    
    # Test Data - including specific ligatures
    test_text = "கு, று, ன், ங்க, ள் - தமிழ் எழுத்துக்கள் சரியாக வருகின்றனவா?"
    print(f"Testing with text: {test_text}")
    
    # Prepare dummy image
    image_path = Config.STORAGE_DIR / "test_base_verify.png"
    from PIL import Image
    img = Image.new('RGB', (1080, 1920), color='#1e1e2f')
    img.save(image_path)
    
    # Prepare dummy audio
    audio_path = Config.STORAGE_DIR / "dummy_verify.mp3"
    if not audio_path.exists():
        import subprocess
        subprocess.run([
            Config.get_ffmpeg(),
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "3",
            "-q:a", "9",
            "-acodec", "libmp3lame",
            "-y",
            str(audio_path)
        ], capture_output=True)

    output_video = Config.STORAGE_DIR / "verify_tamil_ass_v2.mp4"
    
    # Mock scene object
    scene = {
        "scene_number": 1,
        "voice_over": test_text
    }
    
    audio_info = {
        "path": str(audio_path),
        "duration": 3.0
    }
    
    visual_info = {
        "path": str(image_path)
    }
    
    # Run the generation
    print("Generating scene video with ASS subtitles...")
    result_path = await gen.create_scene_video(
        scene,
        audio_info,
        visual_info,
        "default",
        "1080x1920",
        "ta"
    )
    
    if result_path and Path(result_path).exists():
        print(f"✓ Success! Video generated at: {result_path}")
        print("Verification Checklist:")
        print("1. Ligatures (கு, று, ன், ங்க, ள்) should be correctly shaped.")
        print("2. No dotted circles (◌) should appear.")
        print("3. Font should be Nirmala UI (forced via fontsdir).")
    else:
        print("✗ Failure! Video generation failed.")

if __name__ == "__main__":
    asyncio.run(verify_tamil_rendering())
