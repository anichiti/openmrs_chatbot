#!/usr/bin/env python
"""Simple vitals test - show actual response"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

c = ClinicalChatbot()
c.user_role = 'PATIENT'

print("VITALS QUERY TEST\n")
r = c.process_query("What is my child's current weight?", selected_patient_id='100008E')
print("Intent:", r['intent'])
print("\nRESPONSE:")
print(r['response'])
