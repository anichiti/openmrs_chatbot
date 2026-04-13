#!/usr/bin/env python3
"""Test intent classification for vitals history"""

from agents.two_layer_classifier import TwoLayerIntentClassifier

classifier = TwoLayerIntentClassifier()

queries = [
    "vitals history",
    "past vitals",
    "vital readings history",
    "what vitals",
    "current vitals",
    "blood pressure",
]

for query in queries:
    result = classifier.classify(query)
    print(f"Query: '{query}'")
    print(f"  Intent: {result['intent']}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Layer: {result['layer_used']}")
    print()
