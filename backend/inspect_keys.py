import re
import json

with open("postiz_response.txt", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

match = re.search(r"response: (.*)", content)
if match:
    json_str = match.group(1).strip()
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            print("Is List: Yes")
            if len(data) > 0:
                print(f"Keys: {list(data[0].keys())}")
                if "posts" in data[0]:
                    print(f"Posts: {data[0]['posts']}")
        else:
            print("Is List: No")
            print(f"Keys: {list(data.keys())}")
    except:
        # Try raw
        print("Raw parse failed, printing raw snippet")
        print(json_str[:200])
