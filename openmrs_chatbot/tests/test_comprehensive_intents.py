#!/usr/bin/env python3
"""
Comprehensive 2-layer classifier test - all 9 intents + tricky cases
Run this to verify classifier is working correctly before frontend testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.two_layer_classifier import TwoLayerIntentClassifier

classifier = TwoLayerIntentClassifier()

# Test data organized by expected intent
test_suite = {
    "MEDICATION_EMERGENCY": [
        "My child accidentally swallowed too many tablets",
        "I think my son took extra doses of his medicine",
        "The baby got into the medicine cabinet and ate some pills",
        "My daughter may have had too much of her syrup",
        "My child had double the amount of syrup",  # TRICKY TEST 1
        "The child got into the medicine and we are not sure how much he had",  # TRICKY TEST 7
    ],
    
    "MEDICATION_QUERY": [
        "What is the correct dose of paracetamol for this patient?",
        "How much amoxicillin should this child be given based on weight?",
        "Is the current ibuprofen dose right for this patient's age?",
        "Calculate the safe dose for this child",
    ],
    
    "MEDICATION_INFO_QUERY": [
        "What medications is this patient currently on?",
        "List all the medicines prescribed to this child",
        "What drugs is this patient taking right now?",
    ],
    
    "ALLERGY_QUERY": [
        "Does this patient have any allergies?",
        "Can this child be given penicillin?",
        "Is there anything this patient should not be given?",
        "What medicines should we avoid for this child?",
        "Is there anything we need to avoid giving this child?",  # TRICKY TEST 2
        "Can my child have this medicine or will it cause a reaction?",  # TRICKY TEST 4
    ],
    
    "IMMUNIZATION_QUERY": [
        "What vaccines has this child received?",
        "Is this patient up to date with immunizations?",
        "Which shots has this child not yet had?",
        "When is the next vaccine due for this patient?",
        "Has this child had all his shots?",  # TRICKY TEST 6
    ],
    
    "VITALS_QUERY": [
        "What are this patient's current vital signs?",
        "Show me the height and weight of this child",
        "What was the last recorded temperature for this patient?",
        "What is this child's BMI?",
    ],
    
    "MILESTONE_QUERY": [
        "Should this child be walking by now?",
        "What milestones is this patient expected to have reached?",
        "Is it normal that this child is not yet talking?",
        "What developmental milestones has this patient achieved?",
        "My child is 18 months, should he be speaking by now?",  # TRICKY TEST 5
    ],
    
    "PATIENT_RECORD_QUERY": [
        "What is this patient's date of birth?",
        "How old is this child?",
        "What is the gender of this patient?",
        "Show me the basic details of this patient",
        "Can you tell me how old this patient is?",  # TRICKY TEST 3
    ],
    
    "GENERAL_MEDICAL_QUERY": [
        "What are the side effects of amoxicillin?",
        "What is RSV and how does it affect children?",
        "What causes fever in young children?",
        "How does the measles vaccine work?",
    ],
}

print("\n" + "="*120)
print("COMPREHENSIVE 2-LAYER CLASSIFIER TEST - ALL INTENTS")
print("="*120 + "\n")

overall_passed = 0
overall_failed = 0
failed_queries = []

for expected_intent, queries in test_suite.items():
    print(f"\n{'='*120}")
    print(f"Intent: {expected_intent}")
    print(f"{'='*120}")
    
    intent_passed = 0
    intent_failed = 0
    
    for i, query in enumerate(queries, 1):
        result = classifier.classify(query)
        predicted_intent = result["intent"]
        confidence = result["confidence"]
        layer = result["layer_used"]
        
        layer_name = "L1" if layer == 1 else "L2" if layer == 2 else "FB"
        is_correct = predicted_intent == expected_intent
        
        if is_correct:
            status = "[PASS]"
            intent_passed += 1
            overall_passed += 1
        else:
            status = "[FAIL]"
            intent_failed += 1
            overall_failed += 1
            failed_queries.append({
                "query": query,
                "expected": expected_intent,
                "got": predicted_intent,
                "confidence": confidence
            })
        
        print(f"{status} [{layer_name}] Conf: {confidence:.3f} | {query[:70]:70s}")
        if not is_correct:
            print(f"           Expected: {expected_intent} -> Got: {predicted_intent}")
    
    print(f"\nResult for {expected_intent}: {intent_passed}/{len(queries)} passed")

print("\n\n" + "="*120)
print(f"OVERALL RESULTS: {overall_passed}/{overall_passed + overall_failed} passed ({100*overall_passed/(overall_passed+overall_failed):.0f}%)")
print("="*120)

if overall_failed > 0:
    print(f"\n[FAILURES] {overall_failed} FAILURES DETECTED:\n")
    for item in failed_queries:
        print(f"  Query: {item['query']}")
        print(f"  Expected: {item['expected']}")
        print(f"  Got: {item['got']} (confidence: {item['confidence']:.3f})")
        print()
else:
    print("\n[SUCCESS] ALL TESTS PASSED! 2-layer classifier is working perfectly.")
