#!/usr/bin/env python3
"""Test patient ID resolution"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

# Test resolution logic
patient_identifier = "100008E"
print(f"Testing patient resolution for: {patient_identifier}")
print(f"Is digit: {str(patient_identifier).isdigit()}")

if not str(patient_identifier).isdigit():
    print("\nLooks like an identifier, trying to resolve...")
    patient_info = db.verify_patient_exists(patient_identifier)
    print(f"verify_patient_exists result: {patient_info}")
    
    if patient_info and patient_info.get("patient_id"):
        resolved_id = patient_info["patient_id"]
        print(f"Resolved to internal ID: {resolved_id}")
        
        # Test vitals query with resolved ID
        vitals_result = db.get_patient_vitals_history(resolved_id, limit=100)
        vitals_data = vitals_result.get("data", [])
        print(f"\nVitals retrieved: {len(vitals_data)}")
        
        # Group by date
        from collections import defaultdict
        by_date = defaultdict(list)
        for v in vitals_data:
            by_date[v['obs_datetime']].append(v)
        
        print(f"Dates: {len(by_date)}")
        for date_key in sorted(by_date.keys(), reverse=True):
            print(f"  {date_key}: {len(by_date[date_key])} records")
