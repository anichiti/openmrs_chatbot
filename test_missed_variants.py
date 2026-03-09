#!/usr/bin/env python3
"""Test missed vaccines with different wording to avoid misclassification"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from main import ClinicalChatbot

chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"

print("Testing different wordings for missed vaccines question...\n")

questions = [
    "what vaccines are overdue",
    "which vaccines should be given next based on age",  
    "what immunizations are required but not yet given"
]

for q in questions:
    print(f"{'='*70}\nQUESTION: {q}\n{'='*70}\n")
    result = chatbot.process_query(q, selected_patient_id="100008E")
    if result:
        print(result.get('response', 'No response')[:1000])  # First 1000 chars
        print("\n...truncated...\n")
