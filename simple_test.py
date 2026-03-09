#!/usr/bin/env python
"""Simple test to verify medication responses"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

c = ClinicalChatbot()
c.user_role = 'PATIENT'

questions = [
    'What medicine has been prescribed for my child?',
    'Can my child take ibuprofen and paracetamol together?',
    'My child accidentally took two doses - what should I do?',
    'What are the side effects of paracetamol?',
]

for q in questions:
    print(f"\nQ: {q}")
    try:
        r = c.process_query(q, selected_patient_id='100008E')
        print(f"Intent: {r['intent']}")
        print(f"Response preview: {r['response'][:150]}...")
    except Exception as e:
        print(f"Error: {e}")
