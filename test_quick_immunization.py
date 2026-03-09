#!/usr/bin/env python3
"""Quick test of the three main immunization question types"""

import os
import sys

# Set up path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

def test_query(chatbot, question, patient_id="100008E", user_role="DOCTOR"):
    """Test a single query and show the response"""
    print(f"\n{'='*70}")
    print(f"QUESTION: {question}")
    print(f"USER: {user_role} | PATIENT: {patient_id}")
    print(f"{'='*70}")
    
    chatbot.user_role = user_role
    result = chatbot.process_query(user_question=question, selected_patient_id=patient_id)
    
    if result:
        print(result.get('response', 'No response'))
    else:
        print("ERROR: No result returned")

# Initialize
print("Initializing chatbot...")
chatbot = ClinicalChatbot()

# Test the three main question types
test_query(chatbot, "when is the next immunization dose scheduled")
test_query(chatbot, "what vaccines has my child missed")  
test_query(chatbot, "show immunization history")

print(f"\n{'='*70}\nTESTS COMPLETE\n{'='*70}\n")
