#!/usr/bin/env python3
"""Test that problematic queries are now classified correctly."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.intent_classifier import IntentClassifier

classifier = IntentClassifier()

problem_queries = [
    ("What developmental milestones has this patient achieved?", "MILESTONE_QUERY"),
    ("Is there anything this patient should not be given?", "ALLERGY_QUERY"),
    ("What developmental milestones has the child reached?", "MILESTONE_QUERY"),
    ("Is the patient allergic to anything?", "ALLERGY_QUERY"),
    ("What was the last recorded temperature for this patient?", "VITALS_QUERY"),
]

print("\n" + "="*80)
print("TESTING PROBLEMATIC QUERIES WITH ENHANCED EXAMPLES")
print("="*80 + "\n")

for query, expected in problem_queries:
    result = classifier.classify(query)
    predicted = result["intent"]
    confidence = result["confidence"]
    layer = result.get("layer_used", 0)
    layer_name = {0: "Unknown", 1: "Layer 1 (Emergency)", 2: "Layer 2 (Embedding)", 3: "Layer 3 (NLI)"}.get(layer, "Unknown")
    is_correct = predicted == expected
    status = "✅ PASS" if is_correct else "❌ FAIL"
    
    print(f"{status}")
    print(f"  Query:    {query}")
    print(f"  Expected: {expected}")
    print(f"  Got:      {predicted}")
    print(f"  Layer:    {layer_name}, Confidence: {confidence:.4f}")
    print()
