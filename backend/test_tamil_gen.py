import asyncio
import os
import json
import logging
from main import ScriptProcessor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_tamil_enrichment():
    logging.basicConfig(level=logging.INFO)
    
    scenes = [
        {"scene_number": 1, "text": "வானம் நீலமாக உள்ளது", "duration": 5},
        {"scene_number": 2, "text": "குழந்தைகள் விளையாடுகிறார்கள்", "duration": 5}
    ]
    
    print("Testing Tamil enrichment...")
    enriched_scenes = await ScriptProcessor.enrich_scenes_with_voiceover(scenes, language="ta")
    
    print("\nResults:")
    for scene in enriched_scenes:
        print(f"Scene {scene['scene_number']}:")
        print(f"  Description: {scene['text']}")
        print(f"  Voice-over: {scene.get('voice_over', 'MISSING')}")
        
    # Check if voice_over is in Tamil (simple check for non-ASCII or specific range)
    has_tamil = any(ord(c) > 127 for c in enriched_scenes[0].get('voice_over', ''))
    if has_tamil:
        print("\n✓ Success: Voice-over contains non-ASCII characters (likely Tamil).")
    else:
        print("\n✗ Failure: Voice-over appears to be English/ASCII.")

if __name__ == "__main__":
    asyncio.run(test_tamil_enrichment())
