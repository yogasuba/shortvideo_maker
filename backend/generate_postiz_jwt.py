import subprocess
import jwt
from datetime import datetime, timedelta
import json

# Configuration
JWT_SECRET = "random string that is unique to every install - just type random characters here!"
POSTGRES_CONTAINER = "postiz-postgres"
POSTGRES_USER = "postiz-user"
POSTGRES_DB = "postiz-db-local"

print("=" * 60)
print("POSTIZ JWT TOKEN GENERATOR")
print("=" * 60)
print()

# Step 1: List all tables
print("Step 1: Listing database tables...")
result = subprocess.run(
    ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", POSTGRES_USER, "-d", POSTGRES_DB, "-c", 
     "\\dt"],
    capture_output=True,
    text=True
)
print(result.stdout)
print()

# Step 2: Get User ID
print("Step 2: Fetching User ID...")
result = subprocess.run(
    ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", POSTGRES_USER, "-d", POSTGRES_DB, "-t", "-c", 
     'SELECT id FROM "User" LIMIT 1;'],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"Error: {result.stderr}")
    print("Trying alternative table name 'users'...")
    result = subprocess.run(
        ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", POSTGRES_USER, "-d", POSTGRES_DB, "-t", "-c", 
         'SELECT id FROM users LIMIT 1;'],
        capture_output=True,
        text=True
    )

user_id = result.stdout.strip()
print(f"User ID: {user_id}")
print()

# Step 3: Get Organization ID
print("Step 3: Fetching Organization ID...")
result = subprocess.run(
    ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", POSTGRES_USER, "-d", POSTGRES_DB, "-t", "-c", 
     'SELECT id FROM "Organization" LIMIT 1;'],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"Error: {result.stderr}")
    print("Trying alternative table name 'organizations'...")
    result = subprocess.run(
        ["docker", "exec", POSTGRES_CONTAINER, "psql", "-U", POSTGRES_USER, "-d", POSTGRES_DB, "-t", "-c", 
         'SELECT id FROM organizations LIMIT 1;'],
        capture_output=True,
        text=True
    )

org_id = result.stdout.strip()
print(f"Organization ID: {org_id}")
print()

# Step 4: Generate JWT Token
print("Step 4: Generating JWT Token...")
payload = {
    "userId": user_id,
    "orgId": org_id,
    "iat": int(datetime.utcnow().timestamp()),
    "exp": int((datetime.utcnow() + timedelta(days=365)).timestamp())
}

token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
print(f"JWT Token: {token}")
print()

# Step 5: Save to file
print("Step 5: Saving token to postiz_jwt_token.txt...")
with open("postiz_jwt_token.txt", "w") as f:
    f.write(token)
print("✅ Token saved!")
print()

print("=" * 60)
print("NEXT STEPS:")
print("=" * 60)
print("1. Copy the JWT token above")
print("2. Update your .env file:")
print(f"   POSTIZ_API_KEY={token}")
print("3. Restart your backend server")
print("4. Test with: python test_postiz_api.py")
print("=" * 60)
