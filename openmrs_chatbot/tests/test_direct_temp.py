#!/usr/bin/env python3
"""Test direct-data detection for temperature queries."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()

test_queries = [
    "What was the last recorded temperature for this patient?",
    "Last temperature reading?",
    "Temperature for patient?",
]

print("\n" + "="*80)
print("TESTING DIRECT-DATA DETECTION FOR TEMPERATURE QUERIES")
print("="*80 + "\n")

for query in test_queries:
    is_direct, query_types = chatbot.is_direct_data_query(query)
    status = "✅" if is_direct and 'temperature' in (query_types or []) else "❌"
    print(f"{status} Query: '{query}'")
    print(f"   Detected: {is_direct}, Types: {query_types}")
    print()
