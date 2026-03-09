#!/usr/bin/env python3
"""Test that 'last vaccination' queries now work correctly"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

def test_last_vaccination_query():
    print("\n" + "="*90)
    print("TEST: LAST VACCINATION QUERY FIX")
    print("="*90)
    
    chatbot = ClinicalChatbot()
    chatbot.user_role = "PATIENT"
    
    # Test the query that was previously misclassified
    test_cases = [
        {
            "query": "When was my child's last vaccination?",
            "expected": "Most Recent",
            "should_not_have": ["NEXT SCHEDULED", "Diphtheria tetanus and pertussis vaccination on 2026-09-25"],
            "description": "Patient asking for last vaccination"
        },
        {
            "query": "What was the latest vaccine given to my child?",
            "expected": "Most Recent",
            "should_not_have": ["NEXT SCHEDULED"],
            "description": "Patient asking for latest vaccine"
        },
        {
            "query": "When is my child's next vaccination?",
            "expected": ["NEXT SCHEDULED", "2026-09-25"],
            "should_not_have": ["Most Recent"],
            "description": "Patient asking for next vaccination (should still work)"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'─'*90}")
        print(f"TEST {i}: {test_case['description']}")
        print(f"{'─'*90}")
        print(f"Query: '{test_case['query']}'")
        
        result = chatbot.process_query(test_case['query'], selected_patient_id="100008E")
        response = result.get('response', 'No response')
        intent = result.get('intent', 'Unknown')
        
        print(f"\nIntent: {intent}")
        print(f"\nResponse Preview:\n{response[:300]}...\n")
        
        # Check expected content
        passed = True
        expected_list = test_case['expected'] if isinstance(test_case['expected'], list) else [test_case['expected']]
        
        for expected in expected_list:
            if expected in response:
                print(f"✅ FOUND: '{expected}'")
            else:
                print(f"❌ MISSING: Expected '{expected}' in response")
                passed = False
        
        # Check should not have
        for not_expected in test_case.get('should_not_have', []):
            if not_expected in response:
                print(f"❌ SHOULD NOT HAVE: Found '{not_expected}' in response")
                passed = False
            else:
                print(f"✅ CORRECTLY EXCLUDED: '{not_expected}'")
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status}")
    
    print(f"\n{'='*90}")
    print("Testing with DOCTOR role:")
    print(f"{'='*90}\n")
    
    chatbot.user_role = "DOCTOR"
    result = chatbot.process_query("When was the most recent vaccination for this patient?", selected_patient_id="100008E")
    response = result.get('response', 'No response')
    
    print(f"Query: 'When was the most recent vaccination for this patient?'")
    print(f"User Type: Doctor\n")
    print(f"Response:\n{response}\n")
    
    if "MOST RECENT VACCINATION" in response:
        print("✅ Doctor query also working correctly!")
    else:
        print("⚠️ Doctor query needs verification")

if __name__ == "__main__":
    test_last_vaccination_query()
