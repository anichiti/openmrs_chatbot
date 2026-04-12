#!/usr/bin/env python3
"""
End-to-end integration test for 2-layer classifier with main.py
Tests that the new classifier routes to correct handlers in production pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import ClinicalChatbot

def test_integration():
    """Test that classifier works with production ClinicalChatbot."""
    
    print("\n" + "="*100)
    print("END-TO-END INTEGRATION TEST: 2-Layer Classifier in ClinicalChatbot")
    print("="*100 + "\n")
    
    # Initialize chatbot with new 2-layer classifier
    chatbot = ClinicalChatbot()
    print(f"✅ ClinicalChatbot initialized successfully")
    print(f"  Classifier type: {type(chatbot.intent_classifier).__name__}")
    print()
    
    # Test queries covering all 9 intents
    test_cases = [
        # (query, expected_intent, category)
        ("What is the dose of paracetamol for a 5kg child?", "MEDICATION_QUERY", "Medication Dosage"),
        ("Patient overdosed! Emergency!", "MEDICATION_EMERGENCY", "Emergency"),
        ("What medications is patient currently taking?", "MEDICATION_INFO_QUERY", "Medication List"),
        ("Is patient allergic to penicillin?", "ALLERGY_QUERY", "Allergy Check"),
        ("What is patient's blood pressure?", "VITALS_QUERY", "Vital Signs"),
        ("Has patient received all vaccines?", "IMMUNIZATION_QUERY", "Vaccination Status"),
        ("Should 18-month-old be walking?", "MILESTONE_QUERY", "Development"),
        ("What is patient age and date of birth?", "PATIENT_RECORD_QUERY", "Demographics"),
        ("Tell me about diabetes complications", "GENERAL_MEDICAL_QUERY", "Medical Knowledge"),
    ]
    
    print("Testing classification for all 9 intents:")
    print("-" * 100)
    
    passed = 0
    failed = 0
    
    for query, expected_intent, category in test_cases:
        # Call the classification method
        result = chatbot.intent_classifier.classify(query)
        
        predicted_intent = result["intent"]
        confidence = result["confidence"]
        layer = result["layer_used"]
        
        layer_name = "L1 (Keywords)" if layer == 1 else "L2 (Embeddings)" if layer == 2 else "Fallback"
        
        # Check if correct
        is_correct = predicted_intent == expected_intent
        if is_correct:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"
        
        print(f"{status} | {category:20s} | {layer_name:15s} | Conf: {confidence:.3f}")
        print(f"     Query: {query}")
        if is_correct:
            print(f"     Correct: {predicted_intent}")
        else:
            print(f"     Expected: {expected_intent} → Got: {predicted_intent}")
        print()
    
    print("="*100)
    print(f"INTEGRATION TEST RESULTS: {passed}/{len(test_cases)} passed ({100*passed/len(test_cases):.0f}%)")
    print("="*100)
    
    if passed == len(test_cases):
        print("\n✅ All integration tests passed! 2-layer classifier working perfectly.")
        return True
    else:
        print(f"\n❌ {failed} tests failed. Review classification patterns.")
        return False

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
