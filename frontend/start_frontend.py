#!/usr/bin/env python3
"""
Start the frontend web server
"""

import sys
import os
import subprocess
from pathlib import Path

frontend_dir = Path(__file__).parent
os.chdir(str(frontend_dir))

print("\n" + "="*60)
print("Starting Frontend Server")
print("="*60)
print("Frontend will be available at: http://localhost:3000")
print("Make sure the backend server is running on port 8001")
print("\nPress Ctrl+C to stop the server")
print("="*60 + "\n")

# Start simple HTTP server
subprocess.run([sys.executable, "-m", "http.server", "3000"])
