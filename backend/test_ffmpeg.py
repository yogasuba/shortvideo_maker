# test_ffmpeg.py
import subprocess
import sys

def test_ffmpeg():
    print("Testing FFmpeg installation...")
    
    try:
        # Check if ffmpeg is installed
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ FFmpeg is installed")
        else:
            print("✗ FFmpeg is not working properly")
            
        # Test simple video creation
        print("\nTesting video creation...")
        test_cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=red:s=640x480:d=2",
            "-c:v", "libx264",
            "-t", "2",
            "-y",
            "test_video.mp4"
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Video creation test passed")
        else:
            print("✗ Video creation test failed")
            print(f"Error: {result.stderr}")
            
    except FileNotFoundError:
        print("✗ FFmpeg is not installed or not in PATH")
        print("Install FFmpeg:")
        print("  Ubuntu: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from ffmpeg.org")

if __name__ == "__main__":
    test_ffmpeg()