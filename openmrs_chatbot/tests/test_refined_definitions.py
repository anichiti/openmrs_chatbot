#!/usr/bin/env python3
"""Test intent classification with refined NLI definitions."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.intent_classifier import IntentClassifier

def test_classification():
    """Test 7 queries with the refined intent definitions."""
    classifier = IntentClassifier()
    
    test_queries = [
        ("George accidentally took too many tablets", "MEDICATION_EMERGENCY"),
        ("What is the paracetamol dose", "MEDICATION_QUERY"),
        ("What is the ibuprofen dose", "MEDICATION_QUERY"),
        ("What is the SpO2", "VITALS_QUERY"),
        ("how heavy is george", "VITALS_QUERY"),
        ("Should child be walking", "MILESTONE_QUERY"),
        ("What medications on", "MEDICATION_INFO_QUERY"),
    ]
    
    results = []
    print("\n" + "="*80)
    print("TESTING INTENT CLASSIFICATION WITH REFINED DEFINITIONS")
    print("="*80 + "\n")
    
    for query, expected in test_queries:
        result = classifier.classify(query)
        predicted = result["intent"]
        confidence = result["confidence"]
        layer = result.get("layer_used", 0)
        layer_name = {0: "Unknown", 1: "Layer 1 (Emergency)", 2: "Layer 2 (Embedding)", 3: "Layer 3 (NLI)"}.get(layer, "Unknown")
        is_correct = predicted == expected
        status = "✅ PASS" if is_correct else "❌ FAIL"
        
        results.append(is_correct)
        
        print(f"{status}")
        print(f"  Query:    {query}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {predicted}")
        print(f"  Layer:    {layer_name}, Confidence: {confidence:.4f}")
        
        # If Layer 3, show all scores
        if layer == 3 and "all_scores" in result:
            print(f"  All Scores:")
            for intent, score in sorted(result["all_scores"].items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"    - {intent}: {score:.4f}")
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    print("="*80)
    print(f"SUMMARY: {passed}/{total} tests passed ({100*passed/total:.1f}%)")
    print("="*80 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = test_classification()
    sys.exit(0 if success else 1)
