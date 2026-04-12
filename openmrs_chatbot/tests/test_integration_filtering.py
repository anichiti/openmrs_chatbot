#!/usr/bin/env python
"""Integration test - test chatbot responses with specific questions"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import ClinicalChatbot

def test_chatbot_responses():
    """Test the chatbot with specific questions"""
    
    print("\n" + "="*80)
    print("CHATBOT INTEGRATION TEST - SPECIFIC QUESTION FILTERING")
    print("="*80)
    
    chatbot = ClinicalChatbot()
    
    test_cases = [
        ("What is patient 7 name?", "Should return ONLY the patient's name"),
        ("What is patient 7 age?", "Should return ONLY the age"),
        ("What is patient 7 weight and height?", "Should return ONLY weight and height"),
        ("What conditions does patient 7 have?", "Should return ONLY conditions (English only)"),
    ]
    
    for question, expected_behavior in test_cases:
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"Expected: {expected_behavior}")
        print(f"{'-'*80}")
        
        try:
            response = chatbot.process_query(question)
            print(f"Response:\n{response}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("Integration test complete")
    print("="*80)

if __name__ == '__main__':
    test_chatbot_responses()
