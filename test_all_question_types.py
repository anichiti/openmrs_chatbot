#!/usr/bin/env python3
"""Test all immunization question types with the chatbot"""

import os
import sys

# Set up path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot
from datetime import datetime

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def run_query(chatbot, question, patient_id, user_type="doctor"):
    """Run a query and display results"""
    print(f"\nUser Type: {user_type.upper()}")
    print(f"Patient: {patient_id}")
    print(f"Question: {question}")
    print("-" * 80)
    
    try:
        # Set user role on chatbot for this query
        chatbot.user_role = user_type.upper()
        result = chatbot.process_query(
            user_question=question, 
            selected_patient_id=patient_id
        )
        
        if result:
            response = result.get('response', 'No response')
            print("\nRESPONSE:\n")
            print(response)
            return True
        else:
            print("No result returned")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# Initialize the chatbot
print("Initializing chatbot...")
chatbot = ClinicalChatbot()
patient_id = "100008E"

# Test 1: Next scheduled dose
print_section("TEST 1: NEXT SCHEDULED DOSE QUESTION")
questions_next = [
    "when is the next immunization dose scheduled",
    "what is the next vaccine due",
    "when is the next vaccine appointment scheduled"
]

for q in questions_next:
    run_query(chatbot, q, patient_id, "doctor")
    print("\n" + "-" * 80)

# Test 2: Missed vaccines
print_section("TEST 2: MISSED VACCINES QUESTION")
questions_missed = [
    "what vaccines has my child missed",
    "which vaccines are overdue",
    "what vaccines are required but not given yet"
]

for q in questions_missed:
    run_query(chatbot, q, patient_id, "doctor")
    print("\n" + "-" * 80)

# Test 3: Full history
print_section("TEST 3: IMMUNIZATION HISTORY QUESTION")
questions_history = [
    "show me the immunization history",
    "what vaccines has my child received",
    "what immunizations are recommended"
]

for q in questions_history:
    run_query(chatbot, q, patient_id, "doctor")
    print("\n" + "-" * 80)

# Test 4: Patient-friendly responses
print_section("TEST 4: PATIENT-FRIENDLY RESPONSES")
print("\n--- Next dose (patient view) ---")
run_query(chatbot, "when is the next vaccine due", patient_id, "patient")

print("\n" + "-" * 80)
print("\n--- Missed vaccines (patient view) ---")
run_query(chatbot, "what vaccines did I miss", patient_id, "patient")

print_section("ALL TESTS COMPLETE")
