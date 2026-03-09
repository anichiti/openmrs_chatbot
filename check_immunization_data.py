#!/usr/bin/env python3
"""Debug script to check immunization.json data loading"""

import json

with open('openmrs_chatbot/data/immunization.json', 'r') as f:
    data = json.load(f)
    
print(f"Loaded {len(data.get('vaccines', []))} vaccines:")
print()

for vaccine in data.get('vaccines', []):
    name = vaccine.get('name', '')
    age_groups = vaccine.get('recommended_age_groups', [])
    print(f"ID {vaccine.get('id')}: {name}")
    print(f"  Age groups: {age_groups}")
    print()

# Specifically check for DTaP
print("\n" + "="*80)
dtap_found = False
dpt_found = False

for vaccine in data.get('vaccines', []):
    name_lower = vaccine.get('name', '').lower()
    if 'dtap' in name_lower:
        dtap_found = True
        print(f"✓ Found DTaP: {vaccine.get('name')}")
        print(f"  ID: {vaccine.get('id')}")
        print(f"  Age groups: {vaccine.get('recommended_age_groups')}")
    if 'dpt' in name_lower and 'dtap' not in name_lower:
        dpt_found = True
        print(f"✓ Found DPT: {vaccine.get('name')}")
        print(f"  ID: {vaccine.get('id')}")
        print(f"  Age groups: {vaccine.get('recommended_age_groups')}")

if not dtap_found:
    print("✗ DTaP not found in vaccines!")
if not dpt_found:
    print("✗ DPT not found in vaccines!")
