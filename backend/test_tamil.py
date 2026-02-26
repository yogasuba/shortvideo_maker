import requests
import json
import codecs

url = "http://127.0.0.1:8001/api/scripts/preview"
payload = {
    "script": "Artificial intelligence is revolutionizing every industry. From healthcare diagnostics to autonomous vehicles, AI is making our lives easier and more efficient.",
    "scenes_count": 4,
    "language": "ta"
}

log_file = "test_tamil_results.log"

def log(msg):
    print(msg)
    with codecs.open(log_file, "a", "utf-8") as f:
        f.write(msg + "\n")

# Clear log
with open(log_file, "w") as f:
    pass

try:
    log(f"Sending request to {url} with language: {payload['language']}")
    response = requests.post(url, json=payload, timeout=60)
    log(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        log(f"Success! Total scenes: {data['data']['total_scenes']}")
        for i, scene in enumerate(data['data']['scenes']):
            log(f"\nScene {i+1}:")
            log(f"  Original Text: {scene['text']}")
            log(f"  Voice-Over (Tamil?): {scene.get('voice_over', 'N/A')}")
    else:
        log(f"Error: {response.text}")
except Exception as e:
    log(f"Failed to connect: {e}")
