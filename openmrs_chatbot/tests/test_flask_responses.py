#!/usr/bin/env python3
"""
Test all intents via Flask API - shows actual chatbot responses
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

# Use a session to maintain cookies/session state
session = requests.Session()

# First, set the role as doctor
print("Setting up Flask session as doctor...")
try:
    role_response = session.post(
        f"{BASE_URL}/set-role",
        data={"role": "doctor"},  # Use form data, not JSON
        allow_redirects=True  # Follow redirects
    )
    if role_response.status_code not in [200, 302]:
        print(f"Warning: Role setup returned status {role_response.status_code}")
    print("Session initialized.\n")
except Exception as e:
    print(f"Error setting role: {e}")
    print()

# Test suite
test_suite = {
    "MEDICATION_EMERGENCY": [
        "My child accidentally swallowed too many tablets",
        "I think my son took extra doses of his medicine",
        "The baby got into the medicine cabinet and ate some pills",
        "My daughter may have had too much of her syrup",
    ],
    
    "MEDICATION_QUERY": [
        "What is the correct dose of paracetamol for this patient?",
        "How much amoxicillin should this child be given based on weight?",
        "Is the current ibuprofen dose right for this patient's age?",
        "Calculate the safe dose for this child",
    ],
    
    "MEDICATION_INFO_QUERY": [
        "What medications is this patient currently on?",
        "List all the medicines prescribed to this child",
        "What drugs is this patient taking right now?",
    ],
    
    "ALLERGY_QUERY": [
        "Does this patient have any allergies?",
        "Can this child be given penicillin?",
        "Is there anything this patient should not be given?",
        "What medicines should we avoid for this child?",
    ],
    
    "IMMUNIZATION_QUERY": [
        "What vaccines has this child received?",
        "Is this patient up to date with immunizations?",
        "Which shots has this child not yet had?",
        "When is the next vaccine due for this patient?",
    ],
    
    "VITALS_QUERY": [
        "What are this patient's current vital signs?",
        "Show me the height and weight of this child",
        "What was the last recorded temperature for this patient?",
        "What is this child's BMI?",
    ],
    
    "MILESTONE_QUERY": [
        "Should this child be walking by now?",
        "What milestones is this patient expected to have reached?",
        "Is it normal that this child is not yet talking?",
        "What developmental milestones has this patient achieved?",
    ],
    
    "PATIENT_RECORD_QUERY": [
        "What is this patient's date of birth?",
        "How old is this child?",
        "What is the gender of this patient?",
        "Show me the basic details of this patient",
    ],
    
    "GENERAL_MEDICAL_QUERY": [
        "What are the side effects of amoxicillin?",
        "What is RSV and how does it affect children?",
        "What causes fever in young children?",
        "How does the measles vaccine work?",
    ],
}

print("\n" + "="*120)
print("CHATBOT RESPONSE TEST - ALL INTENTS")
print("="*120 + "\n")

# Test patient ID - using a known patient from your system
test_patient_id = "10000A9"

for intent_category, queries in test_suite.items():
    print(f"\n{'='*120}")
    print(f"Intent: {intent_category}")
    print(f"{'='*120}\n")
    
    for i, query in enumerate(queries, 1):
        print(f"[Query {i}] {query}")
        
        try:
            # Send request to Flask API (using session to maintain cookies)
            response = session.post(
                f"{BASE_URL}/api/chat",
                json={
                    "question": query,
                    "patient_id": test_patient_id
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant info
                detected_intent = data.get("intent", "N/A")
                chatbot_response = data.get("response", "No response")
                
                print(f"  INTENT: {detected_intent}")
                print(f"  RESPONSE: {chatbot_response[:150]}{'...' if len(chatbot_response) > 150 else ''}")
                print()
            else:
                print(f"  ERROR: Status {response.status_code}")
                print(f"  Response: {response.text}")
                print()
        except requests.exceptions.ConnectionError:
            print(f"  ERROR: Cannot connect to Flask server at {BASE_URL}")
            print(f"  Make sure Flask is running on http://127.0.0.1:5000\n")
            break  # Stop if connection fails
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            print()
        
        time.sleep(0.5)  # Small delay between requests

print("\n" + "="*120)
print("TEST COMPLETE")
print("="*120 + "\n")
