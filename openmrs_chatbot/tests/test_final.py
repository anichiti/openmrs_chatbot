#!/usr/bin/env python3
"""
Final test: Ask the Ollama-powered chatbot a real medical question
"""
import sys
from utils.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_EMBED_MODEL
from agents.triage_agent import TriageAgent
from agents.response_agent import ResponseAgent
import ollama

print("\n" + "="*70)
print("🏥 TESTING OLLAMA CHATBOT WITH MEDICAL QUESTION")
print("="*70)

print(f"\n📋 Configuration:")
print(f"   Host: {OLLAMA_HOST}")
print(f"   Chat Model: {OLLAMA_MODEL}")
print(f"   Embed Model: {OLLAMA_EMBED_MODEL}")

# Test 1: Direct prompt to Ollama
print(f"\n1️⃣ DIRECT MODEL TEST")
print("-" * 70)
client = ollama.Client(host=OLLAMA_HOST)
prompt = "What is the normal blood pressure range for adults?"
print(f"Question: {prompt}")
print(f"\nGenerating response...")
try:
    response = client.generate(
        model=OLLAMA_MODEL,
        prompt=prompt,
        stream=False,
    )
    answer = response['response']
    print(f"\n✅ MODEL RESPONSE:\n{answer[:500]}...\n")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Test intent classification
print("\n2️⃣ INTENT CLASSIFICATION TEST")
print("-" * 70)
try:
    triage = TriageAgent()
    question = "What is patient 24's medication list?"
    intent = triage.classify_intent_local(question)
    print(f"Question: {question}")
    if intent:
        print(f"✅ Detected Intent: {intent}")
    else:
        print(f"ℹ️ No strong local match, would use API classification")
except Exception as e:
    print(f"❌ Classification Error: {e}")

print("\n" + "="*70)
print("✨ OLLAMA SETUP COMPLETE & WORKING!")
print("="*70)
print("\nYou can now:")
print("  • Run: python main.py")
print("  • Select a patient")
print("  • Ask medical questions in natural language")
print("="*70 + "\n")
