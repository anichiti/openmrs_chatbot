#!/usr/bin/env python3
"""Debug NLI scores for specific queries."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Load NLI model
tokenizer = AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-small")
model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/nli-deberta-v3-small")
model.eval()

intent_defs = {
    "MEDICATION_QUERY": "This is about calculating how much of a medicine to give to a patient. The question asks for a dose amount.",
    "VITALS_QUERY": "This is about measuring a patient's body on a machine or scale. The question asks for a number like oxygen level, weight, or blood pressure.",
    "MILESTONE_QUERY": "This is about whether a child can do things like walking or talking at the right age. The question asks if child development is normal.",
}

queries = [
    "What is the ibuprofen dose",
    "What is the SpO2",
    "how heavy is george",
    "Should child be walking"
]

print("\n" + "="*80)
print("NLI DEBUGGING: What's happening with the model scores?")
print("="*80 + "\n")

for query in queries:
    print(f"Query: '{query}'")
    print(f"{'-'*60}")
    
    for intent, definition in intent_defs.items():
        # The NLI model expects (hypothesis, premise) format - I think
        # Let me try different orders
        inputs = tokenizer(
            query,
            definition,
            truncation=True,
            max_length=256,
            return_tensors="pt"
        )
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
        
        probabilities = torch.softmax(logits, dim=1)
        
        # All three labels
        contradiction = probabilities[0][0].item()
        entailment = probabilities[0][1].item()
        neutral = probabilities[0][2].item()
        
        print(f"  {intent:25s}  | Ent: {entailment:.4f} | Ntr: {neutral:.4f} | Ctd: {contradiction:.4f}")
        print(f"    Definition: {definition[:70]}...")
    
    print()
