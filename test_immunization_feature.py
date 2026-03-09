#!/usr/bin/env python3
"""
Test immunization feature for both PATIENT and DOCTOR roles
Tests immunization history, recommended vaccines, and age-based recommendations
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

def test_immunization_feature():
    """Test immunization queries for both roles"""
    
    chatbot = ClinicalChatbot()
    patient_id = '100008E'
    
    print("=" * 80)
    print("IMMUNIZATION FEATURE TEST")
    print("=" * 80)
    print()
    
    # Test 1: PATIENT - Immunization history
    print("TEST 1: PATIENT - What vaccines has my child received?")
    print("-" * 80)
    chatbot.user_role = "PATIENT"
    result = chatbot.process_query(
        "What vaccines has my child received?",
        selected_patient_id=patient_id
    )
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 2: DOCTOR - Immunization history  
    print("TEST 2: DOCTOR - Show me the immunization record for this patient")
    print("-" * 80)
    chatbot.user_role = "DOCTOR"
    result = chatbot.process_query(
        "Show me the immunization record for this patient",
        selected_patient_id=patient_id
    )
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 3: PATIENT - Upcoming vaccines
    print("TEST 3: PATIENT - What vaccines are due for my child?")
    print("-" * 80)
    chatbot.user_role = "PATIENT"
    result = chatbot.process_query(
        "What vaccines are due for my child?",
        selected_patient_id=patient_id
    )
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 4: DOCTOR - Recommended vaccines
    print("TEST 4: DOCTOR - What's the immunization schedule for this patient?")
    print("-" * 80)
    chatbot.user_role = "DOCTOR"
    result = chatbot.process_query(
        "What's the immunization schedule for this patient?",
        selected_patient_id=patient_id
    )
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 5: PATIENT - Vaccination status
    print("TEST 5: PATIENT - Is my child up to date with vaccinations?")
    print("-" * 80)
    chatbot.user_role = "PATIENT"
    result = chatbot.process_query(
        "Is my child up to date with vaccinations?",
        selected_patient_id=patient_id
    )
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 6: DOCTOR - Immunization status
    print("TEST 6: DOCTOR - Check the immunization status for patient 100008E")
    print("-" * 80)
    chatbot.user_role = "DOCTOR"
    result = chatbot.process_query(
        "Check the immunization status for patient 100008E",
        selected_patient_id=patient_id
    )
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    print("=" * 80)
    print("IMMUNIZATION TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_immunization_feature()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
