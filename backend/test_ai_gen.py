# test_ai_gen.py
import asyncio
import logging
import os
from main import VideoGenerator, Config

# Configure logging to see output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_gen():
    print("Initializing VideoGenerator...")
    gen = VideoGenerator()
    
    prompt = "A futuristic city with flying cars"
    style = "cinematic"
    
    print(f"Testing generation with prompt: '{prompt}' and style: '{style}'")
    result = await gen.generate_visual(prompt, style, 1)
    
    print("\nResult:")
    print(f"URL: {result.get('url')}")
    print(f"Path: {result.get('path')}")
    
    if "fallback" in result.get('url', '') or "visual" in result.get('url', ''):
        if os.path.exists(result.get('path')):
            print(f"✓ File created at {result.get('path')}")
            # Check if it's a real image or just a small fallback
            size = os.path.getsize(result.get('path'))
            print(f"File size: {size} bytes")
            if size > 50000: # PIL gradients are small, AI images are usually > 100KB
                print("✓ Looks like a real AI image!")
            else:
                print("✗ Looks like a fallback gradient or small image.")
        else:
            print("✗ File not found.")
    else:
        print("✗ No result returned.")

if __name__ == "__main__":
    asyncio.run(test_gen())
