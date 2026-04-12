#!/usr/bin/env python3
"""Test the 2-layer classifier to show both layers working."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.two_layer_classifier import TwoLayerIntentClassifier

classifier = TwoLayerIntentClassifier()

# Test cases designed to trigger both layers
test_queries = [
    # Layer 1: Strong keyword matches (should trigger immediately)
    ("Patient took too much medicine emergency!", "MEDICATION_EMERGENCY", "L1 keywords"),
    ("What's the dose of paracetamol?", "MEDICATION_QUERY", "L1 keywords"),
    ("Does patient have drug allergies?", "ALLERGY_QUERY", "L1 keywords"),
    ("What vaccines already given?", "IMMUNIZATION_QUERY", "L1 keywords"),
    
    # Layer 2: Embedding-based (keywords weak, embeddings handle it)
    ("Should this child be walking at 18 months?", "MILESTONE_QUERY", "L2 embeddings"),
    ("Is the patient's blood pressure high?", "VITALS_QUERY", "L2 embeddings"),
    ("What medications currently prescribed?", "MEDICATION_INFO_QUERY", "L2 embeddings"),
    ("Patient age and DOB?", "PATIENT_RECORD_QUERY", "L2 embeddings"),
    
    # Fallback: General knowledge
    ("What causes diabetes?", "GENERAL_MEDICAL_QUERY", "Fallback"),
]

print("\n" + "="*100)
print("2-LAYER CLASSIFIER TEST - SHOWING BOTH LAYERS IN ACTION")
print("="*100 + "\n")

layer1_count = 0
layer2_count = 0
fallback_count = 0
correct = 0

for query, expected_intent, description in test_queries:
    result = classifier.classify(query)
    predicted_intent = result["intent"]
    confidence = result["confidence"]
    layer = result["layer_used"]
    
    layer_name = {
        0: "Fallback",
        1: "L1 (Keywords)",
        2: "L2 (Embedding)"
    }[layer]
    
    is_correct = predicted_intent == expected_intent
    status = "✅ PASS" if is_correct else "❌ FAIL"
    
    if is_correct:
        correct += 1
    
    if layer == 1:
        layer1_count += 1
    elif layer == 2:
        layer2_count += 1
    else:
        fallback_count += 1
    
    print(f"{status} | {layer_name:15s} | Conf: {confidence:.3f}")
    print(f"     Query: {query}")
    print(f"     Expected: {expected_intent} → Got: {predicted_intent} ({description})")
    print()

print("="*100)
print(f"RESULTS: {correct}/{len(test_queries)} correct ({100*correct/len(test_queries):.0f}%)")
print(f"Layer 1 (Keywords): {layer1_count} | Layer 2 (Embeddings): {layer2_count} | Fallback: {fallback_count}")
print("="*100 + "\n")

if correct == len(test_queries):
    print("✅ Perfect accuracy! 2-Layer system is working well.")
else:
    print(f"⚠️  {len(test_queries) - correct} queries need tuning")
