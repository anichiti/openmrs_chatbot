#!/usr/bin/env python3
"""
Test all 12 sample vitals questions from user requirements
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from main import ClinicalChatbot

# Initialize chatbot
print("Initializing Clinical Chatbot...")
chatbot = ClinicalChatbot()
chatbot.user_role = "PATIENT"  # Set role to PATIENT

print("\n" + "="*80)
print("COMPREHENSIVE VITALS AND GROWTH METRICS TESTING - ALL 12 SAMPLE QUESTIONS")
print("="*80)

# All 12 sample questions from user requirements
questions = [
    "What were my child's vitals at the last visit?",
    "What is my child's current weight?",
    "How tall is my child as of the last visit?",
    "What was my child's temperature at the last appointment?",
    "Is my child's blood pressure normal for their age?",
    "Has my child's weight gone up or down since the last visit?",
    "What is my child's BMI — is it healthy?",
    "What was my child's heart rate at the last checkup?",
    "What does my child's oxygen level mean?",
    "What growth percentile is my child on?",
    "Is my child's weight normal for their age?",
    "How has my child's weight changed over the past few months?",
]

for i, question in enumerate(questions, 1):
    print(f"\n[TEST {i}] {question}")
    print("-" * 80)
    
    try:
        result = chatbot.process_query(question, selected_patient_id='100008E')
        
        intent = result.get("intent", "N/A")
        response = result.get("response", "No response")
        
        print(f"Intent: {intent}")
        
        # Show first 150 chars of response
        if len(response) > 150:
            print(f"Response preview: {response[:150]}...")
        else:
            print(f"Response:\n{response}")
        
        print()
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
