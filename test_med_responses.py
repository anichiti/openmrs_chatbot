#!/usr/bin/env python
"""Test and display chatbot responses to medication questions"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'openmrs_chatbot')))

from openmrs_chatbot.main import ClinicalChatbot

def test_medication_responses():
    """Test and display actual responses to medication questions"""
    
    # Initialize chatbot
    chatbot = ClinicalChatbot()
    
    test_cases = [
        {
            "name": "What medicine has been prescribed for my child?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "My child accidentally took two doses of aspirin — what should I do?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "Can my child take ibuprofen and paracetamol together?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "What are the side effects of paracetamol?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "Should my child take this medicine with food or without?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "My child vomited after taking the medicine — should I give another dose?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "Can I crush my child's tablet to mix with food?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
        {
            "name": "My child refuses to take the medicine — can I mix it with juice?",
            "user_type": "patient",
            "patient_id": "100008E",
        },
    ]
    
    print("=" * 100)
    print("MEDICATION QUESTION RESPONSES TEST")
    print("=" * 100)
    
    for idx, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 100}")
        print(f"Question {idx}: {test['name']}")
        print("=" * 100)
        
        try:
            chatbot.user_role = test['user_type'].upper()
            result = chatbot.process_query(
                test['name'],
                selected_patient_id=test['patient_id']
            )
            
            intent = result.get('intent', 'UNKNOWN')
            response = result.get('response', 'No response')
            
            print(f"Intent Detected: {intent}\n")
            print("CHATBOT RESPONSE:")
            print("-" * 100)
            print(response)
            print("-" * 100)
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 100)
    print("TEST COMPLETE - All medication questions tested")
    print("=" * 100)

if __name__ == "__main__":
    test_medication_responses()
