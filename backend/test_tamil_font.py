import asyncio
from pathlib import Path
from main import VideoGenerator, Config
import os

async def test_tamil_font():
    # Mocking necessary parts
    gen = VideoGenerator()
    
    test_text = "வானம் நீலமாக உள்ளது. குழந்தைகள் விளையாடுகிறார்கள்."
    image_path = Config.STORAGE_DIR / "test_base.png"
    output_path = Config.STORAGE_DIR / "test_tamil_output.mp4"
    
    # Create a base image if it doesn't exist
    from PIL import Image
    img = Image.new('RGB', (1080, 1920), color='#1a1a2e')
    img.save(image_path)
    
    print(f"Testing Tamil font rendering for text: {test_text}")
    # We'll just test the image generation part of _create_scene_with_simple_text
    # but we can call the whole method if we have a dummy audio file
    
    dummy_audio = Config.STORAGE_DIR / "dummy.mp3"
    if not dummy_audio.exists():
        # Create a tiny dummy mp3 using ffmpeg
        import subprocess
        subprocess.run([
            Config.get_ffmpeg(),
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "1",
            "-q:a", "9",
            "-acodec", "libmp3lame",
            "-y",
            str(dummy_audio)
        ], capture_output=True)

    result = await gen._create_scene_with_simple_text(
        str(image_path),
        str(dummy_audio),
        output_path,
        1.0,
        test_text,
        "1080x1920",
        "ta"
    )
    
    if result:
        print(f"✓ Success: Video generated at {result}")
        print("Please check the generated video for proper Tamil rendering.")
    else:
        print("✗ Failure: Video generation failed.")

if __name__ == "__main__":
    asyncio.run(test_tamil_font())
