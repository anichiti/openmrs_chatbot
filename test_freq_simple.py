#!/usr/bin/env python3
"""
Test specific frequency questions to verify MEDICATION_ADMINISTRATION_QUERY
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

print("Testing frequency-specific questions...")
chatbot = ClinicalChatbot()

questions = [
    ("How often should I give the medication?", "PATIENT"),
    ("What's the dosing frequency?", "PATIENT"),
    ("How often should I give the medication?", "DOCTOR"),
]

for q, role in questions:
    chatbot.user_role = role
    print(f"\n[{role}] {q}")
    result = chatbot.process_query(q, selected_patient_id='100008E')
    intent = result.get('intent')
    response = result.get('response')
    
    print(f"Intent: {intent}")
    if "Medication Frequency" in response or "Dosing Frequency" in response or "frequency" in response.lower():
        # Show frequency-related content
        lines = response.split('\n')
        for i, line in enumerate(lines[:15]):  # First 15 lines
            if any(kw in line.lower() for kw in ['frequency', 'daily', 'times', 'dose:', '**']):
                print(f"  {line}")
    else:
        # Show first 200 chars
        print(f"  {response[:200]}...")
