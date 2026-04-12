#!/usr/bin/env python3
"""Debug the 2-layer classifier keyword layer."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.two_layer_classifier import TwoLayerIntentClassifier

classifier = TwoLayerIntentClassifier()

# Test cases - focus on showing keyword matching
test_queries = [
    "What's the dose of paracetamol?",
    "Patient overdosed on medicine!",
    "Does patient have allergies?",
    "What vaccines given?",
]

print("\n" + "="*100)
print("DEBUGGING LAYER 1 KEYWORD MATCHING")
print("="*100 + "\n")

for query in test_queries:
    print(f"Query: {query}")
    query_lower = query.lower().strip()
    
    # Get Layer 1 scores
    scores = classifier._keyword_layer(query_lower)
    
    if scores:
        print(f"  Layer 1 Scores: {scores}")
        best_intent = max(scores.items(), key=lambda x: x[1])
        intent_name, score = best_intent
        print(f"  Best: {intent_name} = {score:.3f}")
        print(f"  Triggers Layer 1? {score >= 0.1} (threshold=0.1)")
    else:
        print(f"  Layer 1 Scores: None (no keywords matched)")
    
    print()
