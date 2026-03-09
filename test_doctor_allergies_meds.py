#!/usr/bin/env python3
"""Test allergies and medications for doctor"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

print("Testing allergies and medications for DOCTOR...\n")

# Test 1: General allergies query
print("="*70)
print("TEST 1: Doctor asking about allergies")
print("="*70)
result = chatbot.process_query("what allergies does the patient have", selected_patient_id="100008E")
if result:
    print("\nResponse:\n")
    print(result.get('response', 'No response')[:800])
    print("\n...truncated...\n")

# Test 2: Specific drug check
print("="*70)
print("TEST 2: Doctor asking about penicillin allergy")
print("="*70)
result = chatbot.process_query("can i give penicillin to this patient", selected_patient_id="100008E")
if result:
    print("\nResponse:\n")
    print(result.get('response', 'No response')[:800])
    print("\n...truncated...\n")

# Test 3: Active medications
print("="*70)
print("TEST 3: Doctor asking about active medications")
print("="*70)
result = chatbot.process_query("what medications is the patient currently taking", selected_patient_id="100008E")
if result:
    print("\nResponse:\n")
    print(result.get('response', 'No response')[:800])
    print("\n...truncated...\n")

print("\nAll tests completed.")
