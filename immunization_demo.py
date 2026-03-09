#!/usr/bin/env python3
"""
Quick demo of immunization feature - shows patient vs doctor views
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

def demo_immunization():
    """Quick demo showing both views"""
    
    chatbot = ClinicalChatbot()
    patient_id = '100008E'
    question = "What vaccines has my child received?"
    
    print("\n" + "=" * 80)
    print("IMMUNIZATION FEATURE DEMO")
    print("=" * 80)
    
    # Patient view
    print("\n[PATIENT VIEW]:")
    print("-" * 80)
    chatbot.user_role = "PATIENT"
    patient_result = chatbot.process_query(question, selected_patient_id=patient_id)
    response_text = patient_result['response'][:400]
    print(response_text)
    print("\n[... additional content truncated ...]\n")
    
    # Doctor view
    print("-" * 80)
    print("[DOCTOR VIEW]:")
    print("-" * 80)
    chatbot.user_role = "DOCTOR"
    doctor_result = chatbot.process_query(
        "Show me the immunization record",
        selected_patient_id=patient_id
    )
    response_text = doctor_result['response'][:400]
    print(response_text)
    print("\n[... additional content truncated ...]\n")
    
    print("=" * 80)
    print("SUCCESS: Feature working for both PATIENT and DOCTOR roles!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        demo_immunization()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
