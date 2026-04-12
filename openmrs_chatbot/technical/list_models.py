#!/usr/bin/env python3
"""
List available Ollama models
"""

import ollama
from utils.config import OLLAMA_HOST

try:
    client = ollama.Client(host=OLLAMA_HOST)
    
    print("\nChecking available Ollama models...")
    print("="*60)
    
    response = client.list()
    
    if response and 'models' in response and len(response['models']) > 0:
        print(f"\nFound {len(response['models'])} model(s):\n")
        for model in response['models']:
            name = model.get('name', 'Unknown')
            size = model.get('size', 0)
            size_gb = size / (1024**3)
            print(f"  • {name} ({size_gb:.1f} GB)")
    else:
        print("\nNo models found!")
        print("\nDownload models with:")
        print("  ollama pull llama2")
        print("  ollama pull mistral")
        print("  ollama pull nomic-embed-text")
        
except Exception as e:
    print(f"Error connecting to Ollama: {e}")
    print("\nMake sure Ollama is running: ollama serve")
