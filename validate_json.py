#!/usr/bin/env python3
"""Validate and debug immunization.json loading"""

import json

try:
    with open('openmrs_chatbot/data/immunization.json', 'r') as f:
        data = json.load(f)
    print("✓ JSON is valid")
    print(f"Loaded data keys: {list(data.keys())}")
    vaccines = data.get('vaccines', [])
    print(f"Loaded {len(vaccines)} vaccines")
    for v in vaccines:
        print(f"  - ID {v.get('id')}: {v.get('name')}")
except json.JSONDecodeError as e:
    print(f"✗ JSON parsing error: {e}")
    print(f"  Line {e.lineno}, Column {e.colno}: {e.msg}")
except Exception as e:
    print(f"✗ Error: {e}")
