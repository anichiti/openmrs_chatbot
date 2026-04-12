#!/usr/bin/env python3
"""
Verify configuration is correctly set for OpenMRS + Ollama
"""

import os
import sys
import requests

# Check environment variables
print("\n" + "="*60)
print("CONFIGURATION VERIFICATION")
print("="*60)

print("\nChecking .env file...")
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        content = f.read()
        print(".env file found with credentials:")
        for line in content.split('\n'):
            if line and not line.startswith('#'):
                if 'PASSWORD' in line or 'KEY' in line:
                    key, val = line.split('=', 1)
                    print(f"  {key}={val[:20]}..." if len(val) > 20 else f"  {line}")
                else:
                    print(f"  {line}")
else:
    print("✗ .env file not found")
    sys.exit(1)

print("\nChecking Python modules...")
try:
    import mysql.connector
    print("  mysql-connector-python available")
except ImportError:
    print("  mysql-connector-python NOT installed (run: pip install mysql-connector-python)")

try:
    import ollama
    print("  ollama available")
except ImportError:
    print("  ollama NOT installed (run: pip install ollama)")

try:
    from utils.config import (
        DB_HOST, DB_PORT, DB_NAME, DB_USER, 
        OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_EMBED_MODEL
    )
    print("  Configuration module loads correctly")
    print(f"\n  Database Configuration:")
    print(f"    Host: {DB_HOST}:{DB_PORT}")
    print(f"    Name: {DB_NAME}")
    print(f"    User: {DB_USER}")
    print(f"    Type: MySQL")
    
    print(f"\n  Ollama Configuration:")
    print(f"    Host: {OLLAMA_HOST}")
    print(f"    Chat Model: {OLLAMA_MODEL}")
    print(f"    Embed Model: {OLLAMA_EMBED_MODEL}")
    
except Exception as e:
    print(f"  ✗ Configuration error: {str(e)}")
    sys.exit(1)

print("\n" + "="*60)
print("NEXT STEPS")
print("="*60)
print("""
1. Install dependencies:
   pip install -r requirements.txt

2. Start Ollama service (required):
   ollama serve
   (Keep this terminal open)

3. Download models (in another terminal):
   ollama pull llama2
   ollama pull nomic-embed-text

4. Verify MySQL database is running:
   - Make sure MySQL server is accessible at localhost:3308
   - Database 'chatbot-dev' exists with proper tables
   - User 'openmrs' with password 'openmrs' can access it

5. Test Ollama connection:
   python -c "import ollama; \\
   from utils.config import OLLAMA_HOST, OLLAMA_MODEL; \\
   client = ollama.Client(host=OLLAMA_HOST); \\
   response = client.generate(model=OLLAMA_MODEL, prompt='test', stream=False); \\
   print('Ollama API Working')"

6. Run the chatbot:
   python main.py
""")
print("="*60 + "\n")
