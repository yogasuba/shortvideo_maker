
import asyncio
import os
import subprocess
from pathlib import Path
import logging
from main import VideoGenerator, Config

# Setup logging
logging.basicConfig(level=logging.INFO)

async def verify_refined_pipeline():
    print("Starting Comprehensive Pipeline Verification...")
    
    # Initialize Generator
    gen = VideoGenerator()
    
    # Test Data - Step 5: Glyph Validation Test
    test_text = "ரு, கு, நு, பு - Shaping Test. தமிழ் எழுத்துக்கள் சரியாக வருகின்றனவா?"
    test_text_2 = "இரண்டாம் காட்சி: ங்க, ள்\nதுல்லியமான ரெண்டரிங்"
    
    # 2. Prepare dummy assets
    image_path = Config.STORAGE_DIR / "test_base_verify.png"
    if not image_path.exists():
        from PIL import Image
        img = Image.new('RGB', (1080, 1920), color='#1e1e2f')
        img.save(image_path)
    
    audio_path = Config.STORAGE_DIR / "dummy_verify.mp3"
    if not audio_path.exists():
        subprocess.run([
            Config.get_ffmpeg(),
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "2",
            "-q:a", "9",
            "-acodec", "libmp3lame",
            "-y",
            str(audio_path)
        ], capture_output=True)

    print("Step 1: Generating two scene videos with strict params...")
    
    # Scene 1
    scene1 = {"scene_number": 1, "voice_over": test_text}
    audio1 = {"path": str(audio_path), "duration": 2.0}
    visual1 = {"path": str(image_path)}
    
    video1_path = await gen.create_scene_video(scene1, audio1, visual1, "default", "1080x1920", "ta")
    
    # Scene 2 (with missing audio to test silent generation)
    scene2 = {"scene_number": 2, "voice_over": test_text_2}
    audio2 = {"path": "non_existent.mp3", "duration": 2.0} # This will trigger silent audio
    visual2 = {"path": str(image_path)}
    
    video2_path = await gen.create_scene_video(scene2, audio2, visual2, "default", "1080x1920", "ta")
    
    if not video1_path or not video2_path:
        print("✗ Failure! Scene generation failed.")
        return

    print("Step 2: Concatenating scenes using strict filter complex...")
    final_video_url = await gen._concatenate_videos([video1_path, video2_path], "1080x1920")
    
    if final_video_url:
        final_video_path = Config.STORAGE_DIR / final_video_url.replace('/storage/', '')
        print(f"✓ Success! Final video generated at: {final_video_path}")
        
        print("\nStep 3: Verifying final video metadata with ffprobe...")
        probe_cmd = [
            Config.get_ffprobe(),
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(final_video_path)
        ]
        import json
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        
        v_stream = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
        a_stream = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
        
        sar = v_stream.get('sample_aspect_ratio', '1:1')
        print(f"Video: {v_stream['width']}x{v_stream['height']}, {v_stream['r_frame_rate']}fps, {v_stream['pix_fmt']}, SAR: {sar}")
        print(f"Audio: {a_stream['codec_name']}, {a_stream['sample_rate']}Hz, {a_stream['channels']} channels")
        
        if (v_stream['width'] == 1080 and v_stream['height'] == 1920 and 
            v_stream['pix_fmt'] == 'yuv420p' and a_stream['sample_rate'] == '48000' and
            sar == '1:1'):
            print("✓ Metadata verification PASSED (including SAR 1:1)!")
        else:
            print("✗ Metadata verification FAILED!")
            print("1. Glyph Validation: ரு, கு, நு, பு should be correctly shaped (no detached strokes).")
            print("2. Positioning: Subtitles should appear at the BOTTOM-CENTER (Alignment: 2).")
            print("3. Font Hardening: Font should be Noto Sans Tamil (forced via fontsdir and \\fn).")
            print("4. Verification logs should show 'libass' and 'harfbuzz' usage.")
    else:
        print("✗ Failure! Video concatenation failed.")

if __name__ == "__main__":
    asyncio.run(verify_refined_pipeline())
