#!/usr/bin/env python
"""Test vitals and growth queries"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

c = ClinicalChatbot()
c.user_role = 'PATIENT'

test_questions = [
    "What is my child's current weight?",
    "What were my child's vitals at the last visit?",
    "How tall is my child as of the last visit?",
    "What is my child's BMI — is it healthy?",
    "Is my child's weight normal for their age?",
    "What was my child's temperature at the last appointment?",
]

print("="*80)
print("VITALS AND GROWTH METRICS TESTING")
print("="*80)

for idx, question in enumerate(test_questions, 1):
    print(f"\n[TEST {idx}] {question}")
    print("-" * 80)
    
    try:
        r = c.process_query(question, selected_patient_id='100008E')
        print(f"Intent: {r['intent']}")
        
        # Show first 300 chars of response
        response_preview = r['response'][:300].replace('\n', ' ')
        print(f"Response preview: {response_preview}...")
        
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
