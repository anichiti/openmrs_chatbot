#!/usr/bin/env python3
"""
Test medication frequency queries for both doctor and patient
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

print("Initializing Clinical Chatbot...")
chatbot = ClinicalChatbot()

questions = [
    "What is the frequency of dosing for my child's medication?",
    "How often should I give the active medications?",
    "What's the dosing frequency?",
    "How many times per day should the medication be given?",
]

print("\n" + "="*80)
print("MEDICATION FREQUENCY TESTING - PATIENT ROLE")
print("="*80)

chatbot.user_role = "PATIENT"
for q in questions:
    print(f"\nQuestion: {q}")
    result = chatbot.process_query(q, selected_patient_id='100008E')
    print(f"Intent: {result.get('intent')}")
    print(f"Response Preview:\n{result.get('response')[:300]}...\n")

print("\n" + "="*80)
print("MEDICATION FREQUENCY TESTING - DOCTOR ROLE")
print("="*80)

chatbot.user_role = "DOCTOR"
for q in questions:
    print(f"\nQuestion: {q}")
    result = chatbot.process_query(q, selected_patient_id='100008E')
    print(f"Intent: {result.get('intent')}")
    print(f"Response Preview:\n{result.get('response')[:300]}...\n")
