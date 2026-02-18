import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
print(f"Testing key: {key[:10]}...{key[-5:] if key else 'None'}")

if not key:
    print("No OpenAI API key found!")
    exit(1)

client = OpenAI(api_key=key)

try:
    print("Requesting Tamil translation...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Translate to Tamil. Output ONLY a JSON array of 1 string."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        temperature=0.7,
    )
    content = response.choices[0].message.content.strip()
    print(f"AI Response: {content}")
except Exception as e:
    print(f"OpenAI Error: {e}")
