import asyncio
import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AUDIXA_API_KEY = os.getenv("AUDIXA_API_KEY")

async def test_tamil_tts():
    if not AUDIXA_API_KEY:
        print("AUDIXA_API_KEY not found in .env")
        return

    text = "வணக்கம், இந்த வீடியோ தயாரிப்பாளருக்கான ஆடிசா ஏஐ சோதனையாகும்."
    print(f"Testing Tamil TTS with text: {text}")

    submit_url = "https://api.audixa.ai/v2/tts"
    headers = {
        "x-api-key": AUDIXA_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "voice": "af_aria", # Try one of the free voices
        "model": "base",
        "speed": 1.0,
        "language": "ta"
    }

    print(f"Submitting request to {submit_url}...")
    response = requests.post(submit_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code not in [200, 201]:
        print(f"Failed: {response.status_code} - {response.text}")
        return

    generation_id = response.json().get("generation_id")
    print(f"Generation ID: {generation_id}")

    status_url = f"https://api.audixa.ai/v2/status?generation_id={generation_id}"
    
    print("Polling for results...")
    for _ in range(30):
        status_response = requests.get(status_url, headers=headers, timeout=10)
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"Status: {status}")
            
            if status == "Completed":
                audio_url = status_data.get("url")
                print(f"✓ Success! Audio URL: {audio_url}")
                return
            elif status == "Failed":
                print("Failed at Audixa.")
                break
        
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_tamil_tts())
