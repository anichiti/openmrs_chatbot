#!/usr/bin/env python
"""Test hybrid questions and active medication dosage display"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

c = ClinicalChatbot()
c.user_role = 'PATIENT'

print("\n" + "="*80)
print("TEST 1: HYBRID QUESTION - 'Is aspirin safe for my child? How much can I give?'")
print("="*80)
r = c.process_query('Is aspirin safe for my child? How much can I give?', selected_patient_id='100008E')
print(f"INTENT: {r['intent']}")
print(f"HYBRID: {r.get('is_hybrid_question', False)}")
print("\nRESPONSE:")
print(r['response'])

print("\n" + "="*80)
print("TEST 2: ACTIVE MEDICATIONS - 'What medicine has been prescribed for my child?'")
print("="*80)
r2 = c.process_query('What medicine has been prescribed for my child?', selected_patient_id='100008E')
print(f"INTENT: {r2['intent']}")
print("\nRESPONSE (showing dosage for prescribed meds):")
print(r2['response'])
