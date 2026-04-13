#!/usr/bin/env python3
"""Get detailed encounters and visits"""
import sys
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from main import ClinicalChatbot

print("=" * 80)
print("COMPLETE ENCOUNTERS AND VISITS DATA FOR PATIENT 100008E")
print("=" * 80)

# Create chatbot instance
chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

queries = [
    "Show patient encounters",
    "Patient visit history",
    "When was the last visit?",
]

for query in queries:
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"{'='*80}")
    
    result = chatbot.process_query(query, selected_patient_id="100008E")
    
    print(f"Intent: {result.get('intent')}")
    print(f"Sources: {result.get('sources')}")
    print(f"\nResponse:\n")
    print(result.get('response', 'No response'))
    print()
