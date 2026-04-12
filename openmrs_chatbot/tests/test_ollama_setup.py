#!/usr/bin/env python3
"""
Test Ollama Setup - Verify all components working
"""

import sys
import os

print("\n" + "="*70)
print("OLLAMA SETUP VERIFICATION AND TEST")
print("="*70)

# Test 1: Configuration
print("\n[1] CHECKING CONFIGURATION...")
try:
    from utils.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_EMBED_MODEL
    print(f"   - Ollama Host: {OLLAMA_HOST}")
    print(f"   - Chat Model: {OLLAMA_MODEL}")
    print(f"   - Embedding Model: {OLLAMA_EMBED_MODEL}")
except Exception as e:
    print(f"   ERROR: Configuration Error: {e}")
    sys.exit(1)

# Test 2: Python Package
print("\n[2] CHECKING OLLAMA PYTHON PACKAGE...")
try:
    import ollama
    print(f"   - Ollama package installed: v{ollama.__version__ if hasattr(ollama, '__version__') else 'latest'}")
except Exception as e:
    print(f"   ERROR: Ollama package not installed: {e}")
    sys.exit(1)

# Test 3: Ollama Service Connection
print("\n[3] CONNECTING TO OLLAMA SERVICE...")
try:
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.list()
    print(f"   - Connected to Ollama at {OLLAMA_HOST}")
    models_list = response.get('models', [])
    if not models_list and isinstance(response, dict):
        models_list = response.get('model', [])
    print(f"   - Ollama service is running!")
except Exception as e:
    print(f"   ERROR: Connection Failed: {e}")
    print(f"   TIP: Make sure Ollama is running: ollama serve")
    sys.exit(1)

# Test 4: Chat Model Test
print("\n[4] TESTING CHAT MODEL (llama2)...")
print("   Generating response to: 'What are vital signs?'")
try:
    response = client.generate(
        model=OLLAMA_MODEL,
        prompt="What are vital signs? Keep answer short (2-3 sentences).",
        stream=False,
    )
    answer = response['response'].strip()
    print(f"\n   Model Response:")
    print(f"   {'-'*60}")
    print(f"   {answer[:300]}...")
    print(f"   {'-'*60}")
    print(f"   - Chat model working!")
except Exception as e:
    print(f"   ERROR: Chat Model Error: {e}")
    sys.exit(1)

# Test 5: Embedding Model Test
print("\n[5] TESTING EMBEDDING MODEL (nomic-embed-text)...")
try:
    embedding_response = client.embeddings(
        model=OLLAMA_EMBED_MODEL,
        prompt="medical knowledge"
    )
    embedding = embedding_response['embedding']
    print(f"   - Embedding generated successfully")
    print(f"   - Embedding dimension: {len(embedding)}")
except Exception as e:
    print(f"   ERROR: Embedding Model Error: {e}")
    sys.exit(1)

# Test 6: Intent Classification (using local keywords first)
print("\n[6] TESTING INTENT CLASSIFICATION...")
try:
    from agents.triage_agent import TriageAgent
    triage = TriageAgent()
    
    test_questions = [
        "What is patient 24's weight?",
        "Can she take Metformin?",
        "What vaccines should a 12-month-old get?",
        "When do babies start walking?"
    ]
    
    for question in test_questions:
        intent = triage.classify_intent(question)
        print(f"   - '{question}' -> {intent}")
except Exception as e:
    print(f"   ERROR: Triage Error: {e}")
    sys.exit(1)

# Test 7: Response Generation
print("\n[7] TESTING RESPONSE GENERATION...")
try:
    from agents.response_agent import ResponseAgent
    response_agent = ResponseAgent()
    
    test_data = {
        "kb_content": "Patient with Type 2 Diabetes",
        "patient_data": "Patient 24: Age 65, Weight 53kg",
    }
    
    patient_response = response_agent.generate_patient_response(
        "What signs of diabetes should I watch for?",
        test_data
    )
    print(f"   - Response generated successfully")
    print(f"   - Response preview: {patient_response[:150]}...")
except Exception as e:
    print(f"   ERROR: Response Generation Error: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("ALL TESTS PASSED - OLLAMA IS FULLY OPERATIONAL")
print("="*70)

print("\nNEXT STEPS:")
print("   1. Run: python main.py")
print("   2. Select a patient")
print("   3. Ask a medical question")
print("   4. Get instant AI-powered responses")
print("\nTIP: No more API limits! No more costs! Everything runs locally!")
print("="*70 + "\n")

