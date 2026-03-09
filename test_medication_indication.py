#!/usr/bin/env python3
"""
Test medication indication display for both doctor and patient
Verify indication (reason for medication) is shown when asking about medications
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

print("=" * 80)
print("MEDICATION INDICATION DISPLAY TEST")
print("=" * 80)

chatbot = ClinicalChatbot()

# Test medication queries that should show indication
test_cases = [
    ("What medicines are currently prescribed?", "PATIENT"),
    ("What medications is the patient on?", "DOCTOR"),
    ("Can you list the active medications?", "PATIENT"),
    ("How often should I give the medication?", "PATIENT"),
    ("What's the dosing frequency?", "DOCTOR"),
]

for question, role in test_cases:
    chatbot.user_role = role
    print(f"\n[{role}] Q: {question}")
    print("-" * 80)
    
    result = chatbot.process_query(question, selected_patient_id='100008E')
    intent = result.get('intent')
    response = result.get('response')
    
    print(f"Intent: {intent}")
    
    # Show response with focus on indication
    print("\nResponse:")
    lines = response.split('\n')
    for i, line in enumerate(lines[:25]):  # Show first 25 lines
        print(line)
        if i > 24:
            print("...")
            break

print("\n" + "=" * 80)
print("TEST COMPLETE - Indication should be visible in responses above")
print("=" * 80)
