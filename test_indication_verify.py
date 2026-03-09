#!/usr/bin/env python3
"""
Verify medication indication display for both PATIENT and DOCTOR roles.
Tests actual medication queries to confirm indication field shows correctly.
"""
import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

def test_indication_display():
    """Test medication queries with indication display"""
    
    chatbot = ClinicalChatbot()
    patient_id = '100008E'
    
    print("=" * 70)
    print("TESTING MEDICATION INDICATION DISPLAY")
    print("=" * 70)
    print()
    
    # Test 1: PATIENT view - General medication list
    print("TEST 1: PATIENT - What medications are prescribed?")
    print("-" * 70)
    chatbot.user_role = "PATIENT"
    result = chatbot.process_query(
        "What medications are prescribed?",
        selected_patient_id=patient_id
    )
    print(f"Query: What medications are prescribed?")
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 2: DOCTOR view - General medication list  
    print("TEST 2: DOCTOR - Show me the medications prescribed to this patient")
    print("-" * 70)
    chatbot.user_role = "DOCTOR"
    result = chatbot.process_query(
        "Show me the medications prescribed to this patient",
        selected_patient_id=patient_id
    )
    print(f"Query: Show me the medications prescribed to this patient")
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 3: PATIENT view - Medication frequency
    print("TEST 3: PATIENT - How often should the medications be taken?")
    print("-" * 70)
    chatbot.user_role = "PATIENT"
    result = chatbot.process_query(
        "How often should the medications be taken?",
        selected_patient_id=patient_id
    )
    print(f"Query: How often should the medications be taken?")
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    # Test 4: DOCTOR view - Medication frequency
    print("TEST 4: DOCTOR - What's the frequency of the active medications?")
    print("-" * 70)
    chatbot.user_role = "DOCTOR"
    result = chatbot.process_query(
        "What's the frequency of the active medications?",
        selected_patient_id=patient_id
    )
    print(f"Query: What's the frequency of the active medications?")
    print(f"Intent: {result.get('intent')}")
    print(f"Response:\n{result.get('response')}")
    print()
    
    print("=" * 70)
    print("TEST COMPLETE - Check above for Indication/Used for: fields")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_indication_display()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
