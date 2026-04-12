#!/usr/bin/env python
"""Integration test - BMI retrieval through full chatbot"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import ClinicalChatbot

def test_bmi_through_chatbot():
    """Test BMI retrieval through the full chatbot"""
    
    print("\n" + "="*80)
    print("BMI INTEGRATION TEST - Through Full Chatbot")
    print("="*80)
    
    chatbot = ClinicalChatbot()
    
    test_cases = [
        ("What is patient 7 BMI?", "Should return ONLY the BMI value"),
        ("What is patient 7 weight?", "Should return ONLY weight"),
        ("What is patient 7 height?", "Should return ONLY height"),
        ("What are patient 7 vitals?", "Should return all vitals including calculated BMI"),
    ]
    
    for question, expected_behavior in test_cases:
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"Expected: {expected_behavior}")
        print(f"{'-'*80}")
        
        try:
            response = chatbot.process_query(question)
            print(f"Response:\n{response.get('response', 'No response') if isinstance(response, dict) else response}")
            
            # Check if BMI is in the response for BMI queries
            if 'bmi' in question.lower():
                has_bmi = 'bmi' in str(response).lower()
                print(f"\nBMI present in response: {has_bmi}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("Integration test complete")
    print("="*80)

if __name__ == '__main__':
    test_bmi_through_chatbot()
