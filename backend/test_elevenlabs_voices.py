import os
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

def list_voices():
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("API Key not found!")
        return
    
    client = ElevenLabs(api_key=api_key)
    voices = client.voices.get_all()
    
    print(f"{'Name':<20} | {'Voice ID':<25} | {'Category':<15}")
    print("-" * 65)
    for voice in voices.voices:
        print(f"{voice.name:<20} | {voice.voice_id:<25} | {voice.category:<15}")

if __name__ == "__main__":
    list_voices()
