#!/usr/bin/env python3
"""
Test frequency display for active medications for both doctor and patient
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

print("Initializing Clinical Chatbot...")
chatbot = ClinicalChatbot()

frequency_questions = [
    "How often should the medication be given?",
    "What is the dosing frequency?",
    "What is the frequency of dosing for the active medications?",
]

print("\n" + "="*80)
print("FREQUENCY DISPLAY TEST - PATIENT ROLE")
print("="*80)

chatbot.user_role = "PATIENT"
for q in frequency_questions:
    print(f"\nQuestion: {q}")
    print("-" * 80)
    result = chatbot.process_query(q, selected_patient_id='100008E')
    print(f"Intent: {result.get('intent')}")
    print(f"\nRESPONSE:\n{result.get('response')}\n")

print("\n" + "="*80)
print("FREQUENCY DISPLAY TEST - DOCTOR ROLE")
print("="*80)

chatbot.user_role = "DOCTOR"
for q in frequency_questions:
    print(f"\nQuestion: {q}")
    print("-" * 80)
    result = chatbot.process_query(q, selected_patient_id='100008E')
    print(f"Intent: {result.get('intent')}")
    print(f"\nRESPONSE:\n{result.get('response')}\n")

print("\n" + "="*80)
print("TEST COMPLETE - Frequency information should be displayed above")
print("="*80)
