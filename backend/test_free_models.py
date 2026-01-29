
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Add current dir to path to import main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import ScriptProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(levelname)s: %(message)s'
)

async def test():
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    scenes = [
        {"scene_number": 1, "text": "A majestic dragon flying over a crystalline lake at sunrise.", "duration": 5},
    ]
    
    print("\n--- Starting Generation with FREE models ---")
    processor = ScriptProcessor()
    result = await processor.enrich_scenes_with_voiceover(scenes)
    
    print("\n--- Results ---")
    for scene in result:
        print(f"Text: {scene['text']}")
        print(f"VoiceOver: {scene.get('voice_over', 'MISSING')}")
        is_diff = scene['text'] != scene.get('voice_over')
        print(f"Different? {is_diff}")

if __name__ == "__main__":
    asyncio.run(test())
