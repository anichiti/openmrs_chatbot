#!/usr/bin/env python3
"""Test the doctor query for next scheduled dose"""

import os
import sys

# Set up path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot
from datetime import datetime

print("=" * 80)
print("TESTING: Doctor Query - 'when is the next immunization dose scheduled'")
print("=" * 80)

# Initialize the chatbot
chatbot = ClinicalChatbot()

# Simulate doctor query
user_input = "when is the next immunization dose scheduled"
patient_id = "100008E"

print(f"\nQuery: {user_input}")
print(f"Patient: {patient_id}")
print("-" * 80)

# Process the query
result = chatbot.process_query(user_question=user_input, selected_patient_id=patient_id)

# Display the response
print("\nRESPONSE:\n")
if result:
    print(result.get('response', 'No response'))
else:
    print("No result returned")

print("\n" + "=" * 80)
print("SOURCES:", result.get('sources', []))
print("=" * 80)
