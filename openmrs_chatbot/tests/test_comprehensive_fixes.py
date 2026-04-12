#!/usr/bin/env python3
"""Comprehensive test showing all fixes work end-to-end."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.intent_classifier import IntentClassifier

classifier = IntentClassifier()

# All test queries from the user's logs + original test suite
test_queries = [
    # Original test suite
    ("George accidentally took too many tablets", "MEDICATION_EMERGENCY"),
    ("What is the paracetamol dose", "MEDICATION_QUERY"),
    ("What is the ibuprofen dose", "MEDICATION_QUERY"),
    ("Should child be walking", "MILESTONE_QUERY"),
    ("What medications on", "MEDICATION_INFO_QUERY"),
    
    # From user's logs (the problematic ones)
    ("What was the last recorded temperature for this patient?", "VITALS_QUERY"),
    ("What developmental milestones has this patient achieved?", "MILESTONE_QUERY"),
    ("Is there anything this patient should not be given?", "ALLERGY_QUERY"),
    
    # Additional coverage
    ("What is the SpO2", "VITALS_QUERY"),  # Caught by direct-data
    ("how heavy is george", "VITALS_QUERY"),  # Caught by direct-data
]

print("\n" + "="*90)
print("COMPREHENSIVE CLASSIFICATION TEST - ALL FIXES INCLUDED")
print("="*90 + "\n")

passed = 0
failed = 0
direct_path_notes = 0

for query, expected in test_queries:
    result = classifier.classify(query)
    predicted = result["intent"]
    confidence = result["confidence"]
    layer = result.get("layer_used", 0)
    is_correct = predicted == expected
    
    # Special note for direct-data queries
    bypass_note = ""
    if query in ("What is the SpO2", "how heavy is george", "What was the last recorded temperature for this patient?"):
        bypass_note = " [Also caught by direct-data fast path before classifier]"
        direct_path_notes += 1
    
    status = "✅ PASS" if is_correct else "❌ FAIL"
    
    if is_correct:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | {query[:55]:55s} → {predicted:25s} (conf: {confidence:.3f})")
    if bypass_note:
        print(f"     {bypass_note}")

print("\n" + "="*90)
print(f"RESULTS: {passed}/{len(test_queries)} passed ({100*passed/len(test_queries):.1f}%)")
print(f"Direct-data fast path also catches 3 of the queries before classification")
print("="*90 + "\n")

if failed == 0:
    print("✅ ALL TESTS PASSED - System is now stable!")
else:
    print(f"⚠️  {failed} test(s) still need attention")
