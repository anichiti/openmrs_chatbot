#!/usr/bin/env python
"""Test medication info query output"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

c = ClinicalChatbot()
c.user_role = 'PATIENT'

print("Testing: What medicine has been prescribed for my child?")
print("=" * 80)
r = c.process_query('What medicine has been prescribed for my child?', selected_patient_id='100008E')
print("RESPONSE:\n")
print(r['response'])
print("\n" + "=" * 80)
print("INTENT:", r['intent'])
print("USER TYPE:", r['user_type'])
print("SOURCES:", r['sources'])
