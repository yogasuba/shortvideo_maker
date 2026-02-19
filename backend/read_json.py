import re
import json

with open("postiz_response.txt", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Extract JSON part (after "DEBUG: get_post_status(...) response: ")
match = re.search(r"response: (.*)", content)
if match:
    json_str = match.group(1).strip()
    # It might be a python dict string (single quotes) instead of JSON
    try:
        data = json.loads(json_str)
        print(json.dumps(data, indent=2))
    except:
        # Try to parse python dict string
        try:
            import ast
            data = ast.literal_eval(json_str)
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to parse: {e}")
            print(json_str)
else:
    print("Could not find response pattern")
    print(content)
