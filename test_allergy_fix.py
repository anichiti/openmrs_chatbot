#!/usr/bin/env python3
"""Test the allergy query fix"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

print("Testing the fixed allergy query...\n")

print("="*70)
print("QUERY: list the allergies for this patient")
print("="*70)

result = chatbot.process_query("list the allergies for this patient", selected_patient_id="100008E")

if result:
    print("\nResponse:\n")
    print(result.get('response', 'No response'))
    print("\nIntent:", result.get('intent', 'Unknown'))
    print("Sources:", result.get('sources', []))
