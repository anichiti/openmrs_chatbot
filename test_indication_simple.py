#!/usr/bin/env python3
"""Simple test to show medication with indication"""
import sys
sys.path.insert(0, 'openmrs_chatbot')
from main import ClinicalChatbot

print("Testing medication indication display...")
c = ClinicalChatbot()
c.user_role = "PATIENT"

# Test a medication info query
r = c.process_query("What medications are prescribed?", selected_patient_id='100008E')
print(f"\nIntent: {r.get('intent')}")
print(f"\nResponse:\n{r.get('response')}")
