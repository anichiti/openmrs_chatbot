#!/usr/bin/env python
"""Debug script to check what vital names are being returned"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.sql_agent import SQLAgent
from agents.response_agent import ResponseAgent

sql_agent = SQLAgent()
response_agent = ResponseAgent()

patient_data = sql_agent.query_patient_record(7)

if patient_data and patient_data.get("vitals", {}).get("data"):
    print("VITAL NAMES:")
    print("-" * 60)
    for vital in patient_data["vitals"]["data"]:
        vital_name = vital.get('vital_name', 'Unknown')
        print(f"Name: '{vital_name}'")
        print(f"  Is English: {response_agent._is_english_text(vital_name)}")
        print()
else:
    print("No vitals data found")
