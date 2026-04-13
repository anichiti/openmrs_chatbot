#!/usr/bin/env python3
"""Test encounters feature"""
import sys
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from main import ClinicalChatbot

print("=" * 70)
print("TESTING ENCOUNTERS FEATURE IN SERVER CODE")
print("=" * 70)

# Create chatbot instance
chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

# Test query
query = "Show patient encounters"
print(f"\nQuery: {query}")
print(f"Patient: 100008E (Joshua Johnson)")
print()

# Process the query
result = chatbot.process_query(query, selected_patient_id="100008E")

print("RESULTS:")
print("-" * 70)
print(f"Intent: {result.get('intent')}")
print(f"Sources: {result.get('sources')}")
print()
print("Response:")
print("-" * 70)
print(result.get('response', 'No response'))
print("-" * 70)
