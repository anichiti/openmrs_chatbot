#!/usr/bin/env python
"""Test age-specific formatting"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.sql_agent import SQLAgent
from agents.response_agent import ResponseAgent

sql_agent = SQLAgent()
response_agent = ResponseAgent()

patient_data = sql_agent.query_patient_record(7)

print("Patient data keys:", patient_data.keys())
print()

# Format for age question
question = "What is patient 7 age?"
response = response_agent.format_patient_data_for_llm(patient_data, question=question)
print(f"Response for '{question}':")
print(f"'{response}'")
print()
print(f"Response length: {len(response)}")
print(f"Response is empty: {response == '' or response == 'No patient data available.'}")
