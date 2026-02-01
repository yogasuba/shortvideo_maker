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
try:
    import fastapi
    print("✓ FastAPI is installed")
except ImportError:
    print("✗ FastAPI not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"], check=True)

try:
    import uvicorn
    print("✓ Uvicorn is installed")
except ImportError:
    print("✗ Uvicorn not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn"], check=True)

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
