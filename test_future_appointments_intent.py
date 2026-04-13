#!/usr/bin/env python
"""Test FUTURE_APPOINTMENTS_QUERY intent classification and handling"""
import sys
sys.path.insert(0, 'openmrs_chatbot')

from openmrs_chatbot.agents.two_layer_classifier import TwoLayerIntentClassifier

classifier = TwoLayerIntentClassifier()

test_questions = [
    "Show me the patient's upcoming appointments",
    "What are the future scheduled appointments?",
    "When is the next appointment?",
    "What appointments are coming up?",
    "Future visits scheduled?",
    "Can I see the appointment schedule?",
    "What appointments does the patient have?",
]

print("=" * 80)
print("TESTING FUTURE_APPOINTMENTS_QUERY INTENT CLASSIFICATION")
print("=" * 80)

for question in test_questions:
    result = classifier.classify(question)
    intent = result['intent']
    confidence = result['confidence']
    layer = result['layer_used']
    print(f"\nQuestion: {question}")
    print(f"  Intent: {intent}")
    print(f"  Confidence: {confidence:.4f}")
    print(f"  Layer: {layer}")
    print(f"  Match: {'✓' if intent == 'FUTURE_APPOINTMENTS_QUERY' else '✗'}")

print("\n" + "=" * 80)
