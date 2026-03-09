#!/usr/bin/env python3
"""Test allergies with correct wording for doctor"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

print("Testing allergies for DOCTOR with correct wording...\n")

# Test 1: General allergies query with better wording
print("="*70)
print("TEST 1: Doctor asking about allergy profile")
print("="*70)
result = chatbot.process_query("show allergy profile for patient", selected_patient_id="100008E")
if result:
    print("\nResponse:\n")
    print(result.get('response', 'No response'))
    print("\n")

# Test 2: Specific drug contraindication check
print("="*70)
print("TEST 2: Doctor checking if patient is allergic to penicillin")
print("="*70)
result = chatbot.process_query("is the patient allergic to penicillin", selected_patient_id="100008E")
if result:
    print("\nResponse:\n")
    print(result.get('response', 'No response')[:1000])
    print("\n")

print("Tests completed.")
