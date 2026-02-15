import subprocess

def get_org_api_key():
    cmd = [
        "docker", "exec", "postiz-postgres", "psql", 
        "-U", "postiz-user", "-d", "postiz-db-local", "-t", "-c",
        'SELECT "apiKey" FROM "Organization" LIMIT 1;'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        print("Error:", result.stderr)
        return None

if __name__ == "__main__":
    key = get_org_api_key()
    if key:
        print(f"API Key: {key}")
    else:
        print("Failed to get API key.")
