#!/usr/bin/env python
"""Test script to verify new medication question handlers"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'openmrs_chatbot')))

from openmrs_chatbot.main import ClinicalChatbot

def test_medication_handlers():
    """Test all new medication question types"""
    
    # Initialize chatbot
    chatbot = ClinicalChatbot()
    
    test_cases = [
        {
            "name": "Medication Info Query",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "What medicine has been prescribed for my child?",
            "expected_intent": "MEDICATION_INFO_QUERY"
        },
        {
            "name": "Medication Side Effects Query",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "What are the side effects of paracetamol?",
            "expected_intent": "MEDICATION_SIDE_EFFECTS_QUERY"
        },
        {
            "name": "Medication Emergency - Overdose",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "My child accidentally took two doses of aspirin — what should I do?",
            "expected_intent": "MEDICATION_EMERGENCY_QUERY"
        },
        {
            "name": "Medication Compatibility Query",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "Can my child take ibuprofen and paracetamol together?",
            "expected_intent": "MEDICATION_COMPATIBILITY_QUERY"
        },
        {
            "name": "Medication Administration - With Food",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "Should my child take this medicine with food or without?",
            "expected_intent": "MEDICATION_ADMINISTRATION_QUERY"
        },
        {
            "name": "Medication Administration - Vomited",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "My child vomited after taking the medicine — should I give another dose?",
            "expected_intent": "MEDICATION_ADMINISTRATION_QUERY"
        },
        {
            "name": "Medication Administration - Crushing",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "Can I crush my child's tablet to mix with food?",
            "expected_intent": "MEDICATION_ADMINISTRATION_QUERY"
        },
        {
            "name": "Medication Administration - Refused",
            "user_type": "patient",
            "patient_id": "100008E",
            "question": "My child refuses to take the medicine — can I mix it with juice?",
            "expected_intent": "MEDICATION_ADMINISTRATION_QUERY"
        },
    ]
    
    print("=" * 80)
    print("TESTING NEW MEDICATION QUESTION HANDLERS")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\n[TEST] {test['name']}")
        print(f"   Question: {test['question']}")
        print(f"   Expected Intent: {test['expected_intent']}")
        
        try:
            # Set user role based on test case
            chatbot.user_role = test['user_type'].upper()
            
            # Process the query
            result = chatbot.process_query(
                test['question'],
                selected_patient_id=test['patient_id']
            )
            
            actual_intent = result.get('intent', 'UNKNOWN')
            print(f"   Actual Intent: {actual_intent}")
            
            if actual_intent == test['expected_intent']:
                print(f"   [PASS] Intent correctly classified")
                response_preview = result['response'][:100].replace('\n', ' ')
                print(f"   Response Preview: {response_preview}...")
                passed += 1
            else:
                print(f"   [FAIL] Expected {test['expected_intent']}, got {actual_intent}")
                failed += 1
                
        except Exception as e:
            print(f"   [ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_medication_handlers()
    sys.exit(0 if success else 1)
