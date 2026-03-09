#!/usr/bin/env python3
"""
Test script to demonstrate the new patient-focused interactive mode
"""

from main import ClinicalChatbot

def test_patient_focused():
    print("\n" + "="*60)
    print("TESTING PATIENT-FOCUSED INTERACTIVE MODE")
    print("="*60)
    
    chatbot = ClinicalChatbot()
    
    # Simulate selecting patient 2
    print("\n[TEST] Simulating patient selection and queries")
    print("-"*60)
    
    # Get patient 2 details
    print("\n1. Fetching Patient ID 2 details...")
    result = chatbot.sql_agent.db.connect()
    if result:
        patient_result = chatbot.sql_agent.db.get_patient_by_id("2")
        chatbot.sql_agent.db.disconnect()
        
        if patient_result['data'] and len(patient_result['data']) > 0:
            patient_data = patient_result['data'][0]
            print("   Found patient")
            print(f"   - Patient ID: 2")
            print(f"   - Gender: {patient_data.get('gender', 'N/A')}")
            print(f"   - Birth Date: {patient_data.get('birthdate', 'N/A')}")
            print(f"   - Address: {patient_data.get('address1', 'N/A')}")
    
    # Test query about patient
    print("\n2. Testing query: 'What are the recent observations for this patient?'")
    query = "What are the recent observations for patient 2?"
    result = chatbot.process_query(query)
    
    print("   ✓ Query processed")
    print(f"   - User Type: {result['user_type']}")
    print(f"   - Intent: {result['intent']}")
    print(f"   - Patient ID: {result.get('patient_id')}")
    print(f"   - Sources: {result['sources']}")
    print(f"\n   Response (first 300 chars):")
    print(f"   {result['response'][:300]}...")
    
    # Test another query
    print("\n3. Testing query: 'Show me patient 2's medical history'")
    query2 = "Show me patient 2's medical history"
    result2 = chatbot.process_query(query2)
    
    print("   ✓ Query processed")
    print(f"   - User Type: {result2['user_type']}")
    print(f"   - Intent: {result2['intent']}")
    print(f"   - Patient ID: {result2.get('patient_id')}")
    print(f"\n   Response (first 300 chars):")
    print(f"   {result2['response'][:300]}...")
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nTo run interactively, execute: python main.py")
    print("\nThe interactive mode will:")
    print("  1. Ask you to select a patient (by ID, name, or list)")
    print("  2. Display patient's medical record details")
    print("  3. Allow you to ask queries about that specific patient")
    print("  4. Let you 'back' to select another patient")
    print("  5. Let you 'exit' to quit\n")

if __name__ == "__main__":
    test_patient_focused()
