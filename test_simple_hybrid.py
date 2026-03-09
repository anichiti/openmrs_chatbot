#!/usr/bin/env python
"""Simple test of hybrid and med dosage"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

c = ClinicalChatbot()
c.user_role = 'PATIENT'

# Test 1: Hybrid question
print("TEST 1: Hybrid Question")
print("-" * 50)
r = c.process_query('Is aspirin safe for my child? How much can I give?', selected_patient_id='100008E')
print(f"Intent: {r['intent']}")
if 'is_hybrid_question' in r:
    print(f"Hybrid Question: {r['is_hybrid_question']}")
# Print key response lines
lines = r['response'].split('\n')
for i, line in enumerate(lines):
    if 'allergy' in line.lower() or 'safe' in line.lower() or 'dosage' in line.lower() or 'consult' in line.lower():
        print(f"  {line}")

print("\nTEST 2: Active Medications")
print("-" * 50)
r2 = c.process_query('What medicine has been prescribed for my child?', selected_patient_id='100008E')
print(f"Intent: {r2['intent']}")
# Print response showing that dosage is visible
lines2 = r2['response'].split('\n')
for i, line in enumerate(lines2):
    if 'dose' in line.lower() or 'frequency' in line.lower() or '**' in line:
        print(f"  {line}")
