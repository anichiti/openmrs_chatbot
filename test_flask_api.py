#!/usr/bin/env python3
"""Test Flask API directly"""
import requests
import json
import time

# Give server time to handle previous request
time.sleep(1)

base_url = "http://localhost:5000"

print("=" * 70)
print("TESTING FLASK API DIRECTLY")
print("=" * 70)

# Create session and set role
session = requests.Session()

print("\n1. Setting role to DOCTOR...")
response = session.post(f"{base_url}/set-role", json={"role": "doctor"})
print(f"   Status: {response.status_code}")

# Now test the API
print("\n2. Sending encounters query to API...")
query_data = {
    "question": "Show patient encounters",
    "patient_id": "100008E"
}

response = session.post(f"{base_url}/api/chat", json=query_data)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print("\n3. API Response:")
    print("-" * 70)
    print(f"Intent: {result.get('intent')}")
    print(f"Sources: {result.get('sources')}")
    print(f"Response (first 500 chars):")
    resp_text = result.get('response', '')
    print(resp_text[:500] if resp_text else "EMPTY RESPONSE")
    print("-" * 70)
else:
    print(f"ERROR: {response.text}")
