#!/usr/bin/env python3
"""
Start the backend server with proper configuration
"""

import sys
import os
import subprocess
from pathlib import Path

# Set up the path
backend_dir = Path(__file__).parent
os.chdir(str(backend_dir))

# Check if required modules are installed
# Map import name to pip install name
REQUIRED_PACKAGES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "boto3": "boto3",
    "botocore": "botocore",
    "sqlalchemy": "sqlalchemy",
    "gtts": "gtts",
    "PIL": "pillow",
    "requests": "requests",
    "replicate": "replicate",
    "elevenlabs": "elevenlabs",
    "openai": "openai",
    "dotenv": "python-dotenv"
}

def check_and_install_dependencies():
    import importlib
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True)
    else:
        print("All dependencies are satisfied.")

check_and_install_dependencies()

# Enable UTF-8 for console output
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Start the server
print("\n" + "="*60)
print("Starting Backend Server")
print("="*60)
print("API will be available at: http://localhost:8001")
print("Config endpoint: http://localhost:8001/api/config")
print("Voices endpoint: http://localhost:8001/api/config (voices in response)")
print("\nPress Ctrl+C to stop the server")
print("="*60 + "\n")

# Run uvicorn
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", "8001",
    "--reload"
])
