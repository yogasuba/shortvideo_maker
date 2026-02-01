#!/usr/bin/env python3
"""
Test Tamil story rendering with the fixed drawtext filter
"""

import requests
import json
import time

# Your Tamil story
TAMIL_STORY = """புத்திசாலி நரி

ஒரு நாள், ஒரு நரி காட்டில் திரிந்து கொண்டிருந்தது. அதற்கு மிகவும் பசி எடுத்தது. சிறிது தூரத்தில், ஒரு திராட்சைத் தோப்பைப் பார்த்தது.

தோப்புக்குள் நுழைந்து பார்த்தது. அங்கு ஒரு கொடியில் திராட்சைப் பழங்கள் தொங்கிக் கொண்டிருந்தன. ஆனால், அவை மிக உயரத்தில் இருந்தன.

நரி துள்ளித் துள்ளிக் குதித்தது. ஆனால், திராட்சைப் பழங்களை அடைய முடியவில்லை. பல முறை முயன்றும் பலன் இல்லை.

கடைசியாக, நரி பழங்களைப் பார்த்துக் கொண்டே சொன்னது:
"இந்தத் திராட்சைப் பழங்கள் புளிப்பாகத்தான் இருக்கும். நான் இவற்றை வேண்டாம்!"

இப்படிச் சொல்லி, அது அங்கிருந்து நடந்து சென்றது."""

API_URL = "http://localhost:8001"

def test_tamil_story():
    """Test rendering Tamil story"""
    
    print("\n" + "="*60)
    print("TAMIL STORY RENDERING TEST")
    print("="*60)
    
    print("\n✓ Story submitted for processing:")
    print("-" * 60)
    print(TAMIL_STORY[:100] + "...")
    print("-" * 60)
    
    # Create video request
    payload = {
        "script": TAMIL_STORY,
        "language": "ta",
        "voice": "21m00Tcm4TlvDq8ikWAM",  # Rachel voice
        "style": "pexels"
    }
    
    print("\n📤 Sending request to backend...")
    try:
        response = requests.post(f"{API_URL}/api/videos/create", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            project_id = data.get("project_id")
            print(f"✓ Project created: {project_id}")
            
            # Poll for completion
            print("\n⏳ Waiting for video generation...")
            for i in range(30):  # 30 second timeout
                status_response = requests.get(f"{API_URL}/api/projects/{project_id}/status")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status", "unknown")
                    progress = status_data.get("progress", 0)
                    
                    print(f"  [{i+1}] Status: {status} ({progress}%)")
                    
                    if status == "completed":
                        video_path = status_data.get("output_video")
                        print(f"\n✅ SUCCESS: Video created!")
                        print(f"   Location: {video_path}")
                        return True
                    elif status == "failed":
                        error = status_data.get("error", "Unknown error")
                        print(f"\n❌ FAILED: {error}")
                        return False
                
                time.sleep(1)
            
            print("\n⚠️ Timeout waiting for video generation")
            return False
        else:
            print(f"❌ Error: Status {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_tamil_story()
    
    print("\n" + "="*60)
    if success:
        print("✅ TAMIL STORY RENDERING TEST PASSED")
    else:
        print("❌ TAMIL STORY RENDERING TEST FAILED")
    print("="*60)
