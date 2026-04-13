#!/usr/bin/env python
"""Test full FUTURE_APPOINTMENTS_QUERY flow"""
import sys
sys.path.insert(0, 'openmrs_chatbot')

from openmrs_chatbot.main import ClinicalChatbot

chatbot = ClinicalChatbot()

# Test with patient ID (Joshua Johnson = 15)
print("=" * 80)
print("TESTING FUTURE_APPOINTMENTS_QUERY FULL FLOW")
print("=" * 80)

test_questions = [
    "What are the patient's upcoming appointments?",
    "When is the next appointment?",
    "What appointments are scheduled?",
]

for question in test_questions:
    print(f"\nQuery: {question}")
    print("-" * 80)
    
    result = chatbot.process_query(
        user_question=question,
        selected_patient_id=15
    )
    
    print(f"Intent: {result.get('intent', 'UNKNOWN')}")
    print(f"Sources: {result.get('sources', [])}")
    print(f"\nResponse:\n{result.get('response', 'ERROR')}")
    print()

print("=" * 80)
print("\nTesting with different query:")
print("=" * 80)

result = chatbot.process_query(
    user_question="What appointments do I have coming up?",
    selected_patient_id=15
)

print(f"Intent: {result.get('intent', 'UNKNOWN')}")
print(f"Sources: {result.get('sources', [])}")
print(f"\nResponse:\n{result.get('response', 'ERROR')}")
