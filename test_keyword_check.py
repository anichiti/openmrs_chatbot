#!/usr/bin/env python3
"""
Verify frequency keyword matching
"""

import sys
sys.path.insert(0, 'openmrs_chatbot')

from agents.triage_agent import INTENT_KEYWORDS

print("Checking MEDICATION_ADMINISTRATION_QUERY frequency keywords:")
print("-" * 80)

keywords = INTENT_KEYWORDS['MEDICATION_ADMINISTRATION_QUERY']['keywords']
frequency_keywords = [kw for kw in keywords if any(term in kw for term in ['frequency', 'often', 'times', 'interval', 'daily'])]

print(f"Frequency-related keywords found: {len(frequency_keywords)}")
for kw in frequency_keywords:
    print(f"  - {kw}")

print("\n" + "-" * 80)
print("Testing substring matching:")
test_questions = [
    "What's the dosing frequency?",
    "How often should I give the medication?",
    "What is the frequency of dosing?",
]

for q in test_questions:
    q_lower = q.lower()
    matches = [kw for kw in keywords if kw in q_lower]
    print(f"\nQ: {q}")
    print(f"  Matches found: {len(matches)}")
    for match in matches:
        print(f"    - '{match}'")
