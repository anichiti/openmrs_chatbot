#!/usr/bin/env python3
"""
Test medication frequency display for both doctor and patient
Verify frequency information is shown when asked about dosing frequency
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

print("=" * 80)
print("MEDICATION FREQUENCY DISPLAY - ENHANCED HANDLERS")
print("=" * 80)

chatbot = ClinicalChatbot()

# Test frequency questions
frequency_tests = [
    ("How often should I give the medication?", "PATIENT", "MEDICATION_ADMINISTRATION_QUERY"),
    ("What is the dosing frequency?", "PATIENT", "MEDICATION_ADMINISTRATION_QUERY"),
    ("How often should I give the medication?", "DOCTOR", "MEDICATION_ADMINISTRATION_QUERY"),
]

for question, role, expected_intent in frequency_tests:
    chatbot.user_role = role
    print(f"\n[{role}] Q: {question}")
    print(f"Expected Intent: {expected_intent}")
    print("-" * 80)
    
    result = chatbot.process_query(question, selected_patient_id='100008E')
    actual_intent = result.get('intent')
    response = result.get('response')
    
    print(f"Actual Intent: {actual_intent}")
    
    # Check if intent is correct
    if actual_intent == expected_intent:
        print("✓ CORRECT INTENT")
    else:
        print("✗ WRONG INTENT")
    
    # Show frequency-related lines from response
    print("\nResponse (frequency-related lines):")
    lines = response.split('\n')
    for line in lines[:20]:
        if any(kw in line.lower() for kw in ['frequency', 'daily', 'times', 'dose:', 'medication', '**']):
            print(f"  {line}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
