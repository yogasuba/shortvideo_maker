import requests
import json
import time

API_KEY = "adx_1BwYDaoWufWd5R_AYz5QKsbXmOwV2mEVCVZ_Dvk47qQ"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def test_audixa():
    # 1. Submit
    submit_url = "https://api.audixa.ai/v2/tts"
    payload = {
        "text": "Hello, this is a test of the Audixa AI integration for the video maker.",
        "voice": "am_ethan",
        "model": "base",
        "speed": 1.0
    }
    
    print(f"Submitting to {submit_url}...")
    r = requests.post(submit_url, headers=HEADERS, json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    
    if r.status_code != 200:
        return
        
    generation_id = r.json().get("generation_id")
    print(f"Generation ID: {generation_id}")
    
    # 2. Poll
    status_url = f"https://api.audixa.ai/v2/status?generation_id={generation_id}"
    for i in range(10):
        print(f"Polling attempt {i+1}...")
        r = requests.get(status_url, headers=HEADERS)
        data = r.json()
        print(f"Status: {data.get('status')}")
        if data.get("status") == "Completed":
            print(f"Success! URL: {data.get('url')}")
            return
        elif data.get("status") == "Failed":
            print("Failed.")
            return
        time.sleep(2)

if __name__ == "__main__":
    test_audixa()
