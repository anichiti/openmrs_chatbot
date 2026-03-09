#!/usr/bin/env python3
"""
Test that doctor queries for different allergy types return different filtered responses.

Expected Results:
1. "list all the allergies for the patient" → Full profile (2 allergies)
2. "does this patient has any food allergy" → No food allergies message
3. "to which drug is the patient allergic" → Only Penicillin drug allergy
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from openmrs_chatbot.main import ClinicalChatbot

def test_doctor_allergy_type_filtering():
    print("\n" + "="*90)
    print("TESTING DOCTOR ALLERGY TYPE-SPECIFIC FILTERING")
    print("="*90)
    
    chatbot = ClinicalChatbot()
    patient_id = "100008E"
    patient_name = "Joshua"
    
    # Test queries - all asking about different aspects
    test_cases = [
        {
            "query": "list all the allergies for the patient",
            "user_type": "doctor",
            "expected_content": ["Penicillin", "Dust", "DRUG ALLERGIES", "ENVIRONMENT ALLERGIES"],
            "test_name": "GENERAL Profile - All Allergies"
        },
        {
            "query": "does this patient has any food allergy",
            "user_type": "doctor",
            "expected_content": ["No documented food allergies", "FOOD"],
            "not_expected_content": ["Penicillin", "Dust"],
            "test_name": "FOOD Type - Should be None"
        },
        {
            "query": "to which drug is the patient allergic",
            "user_type": "doctor",
            "expected_content": ["Penicillin", "DRUG"],
            "not_expected_content": ["Dust", "ENVIRONMENT"],
            "test_name": "DRUG Type - Only Penicillin"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'─'*90}")
        print(f"TEST {i}: {test_case['test_name']}")
        print(f"{'─'*90}")
        print(f"Query: '{test_case['query']}'")
        print(f"User Type: {test_case['user_type']}")
        
        response = processor.process_query(
            test_case['query'],
            patient_id=patient_id,
            patient_name=patient_name,
            user_type=test_case['user_type']
        )
        
        print(f"\nResponse:\n{response}")
        
        # Check expected content
        passed = True
        for expected in test_case['expected_content']:
            if expected not in response:
                print(f"❌ MISSING: Expected '{expected}' in response")
                passed = False
            else:
                print(f"✅ FOUND: '{expected}'")
        
        # Check not expected content
        if 'not_expected_content' in test_case:
            for not_expected in test_case['not_expected_content']:
                if not_expected in response:
                    print(f"❌ SHOULD NOT HAVE: Found '{not_expected}' in response")
                    passed = False
                else:
                    print(f"✅ CORRECTLY EXCLUDED: '{not_expected}'")
        
        results.append({
            "test": test_case['test_name'],
            "passed": passed,
            "response_length": len(response)
        })
    
    # Summary
    print(f"\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")
    
    passed_count = sum(1 for r in results if r['passed'])
    total_count = len(results)
    
    for result in results:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"{status} - {result['test']} (response length: {result['response_length']} chars)")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED - Doctor allergy filtering working correctly!")
    else:
        print(f"\n⚠️ {total_count - passed_count} test(s) failed")

if __name__ == "__main__":
    test_doctor_allergy_type_filtering()
