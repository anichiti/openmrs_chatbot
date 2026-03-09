#!/usr/bin/env python3
"""Debug file content and JSON parsing"""

import json

# Read raw file content
with open('openmrs_chatbot/data/immunization.json', 'rb') as f:
    raw_content = f.read()

print(f"File size: {len(raw_content)} bytes")
print(f"First 100 bytes (repr): {repr(raw_content[:100])}")
print(f"Last 200 bytes (repr): {repr(raw_content[-200:])}")
print()

# Try to parse
try:
    data = json.loads(raw_content)
    vaccines = data.get('vaccines', [])
    print(f"Successfully parsed {len(vaccines)} vaccines")
    
    # Print all vaccine IDs and names
    for v in vaccines:
        print(f"  ID {v.get('id')}: {v.get('name')}")
    
    # Check what's after vaccine ID 5
    if len(vaccines) >= 5:
        print(f"\nLast vaccine (ID {vaccines[-1].get('id')}): {vaccines[-1].get('name')}")
        print(f"Does it have 'DTaP' in name? {'dtap' in vaccines[-1].get('name', '').lower()}")
        
except json.JSONDecodeError as e:
    print(f"Error: {e}")
