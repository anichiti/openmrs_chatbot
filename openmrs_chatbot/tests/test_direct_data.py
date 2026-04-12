#!/usr/bin/env python3
"""Test that direct-data detector catches the queries."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()

test_queries = [
    ("What is the SpO2", "VITALS_QUERY"),
    ("how heavy is george", "VITALS_QUERY"),
    ("what is the spo2", "VITALS_QUERY"),
    ("oxygen level", "VITALS_QUERY"),
    ("how tall is the patient", "VITALS_QUERY"),
]

print("\n" + "="*80)
print("TESTING DIRECT-DATA QUERY DETECTION")
print("="*80 + "\n")

for query, expected_type in test_queries:
    is_direct, query_types = chatbot.is_direct_data_query(query)
    
    status = "✅" if is_direct else "❌"
    print(f"{status} Query: '{query}'")
    print(f"   Direct data detected: {is_direct}")
    print(f"   Query types: {query_types}")
    print()
