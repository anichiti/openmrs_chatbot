#!/usr/bin/env python3
"""Test the missed vaccinations query fix"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

print("Testing the fixed missed vaccinations query...\n")

print("="*70)
print("QUERY: what are the missed vaccinations")
print("="*70)

result = chatbot.process_query("what are the missed vaccinations", selected_patient_id="100008E")

if result:
    print("\nResponse:\n")
    response = result.get('response', 'No response')
    # Show first 800 chars
    if len(response) > 800:
        print(response[:800])
        print("\n... [truncated for space] ...\n")
    else:
        print(response)
    print("\nIntent:", result.get('intent', 'Unknown'))
    print("Sources:", result.get('sources', []))
