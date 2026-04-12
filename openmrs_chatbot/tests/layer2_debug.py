#!/usr/bin/env python3
"""Check Layer 2 (embedding) scores for the two failing queries."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.intent_classifier import IntentClassifier

classifier = IntentClassifier()

test_queries = [
    "What is the SpO2",
    "how heavy is george"
]

print("\n" + "="*80)
print("LAYER 2 EMBEDDING SCORES FOR FAILING QUERIES")
print("="*80 + "\n")

for query in test_queries:
    # Call the embedding classification directly
    embedding_result = classifier._classify_by_embedding(query)
    
    print(f"Query: '{query}'")
    print(f"  Predicted Intent: {embedding_result['intent']}")
    print(f"  Confidence: {embedding_result['confidence']:.4f}")
    print(f"  Would pass threshold 0.65? {embedding_result['confidence'] >= 0.65}")
    print(f"  Would pass threshold 0.60? {embedding_result['confidence'] >= 0.60}")
    print(f"  Would pass threshold 0.55? {embedding_result['confidence'] >= 0.55}")
    print()
