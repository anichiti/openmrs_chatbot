#!/usr/bin/env python3
"""Test vitals history retrieval end-to-end"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

# Test: Resolve identifier "100008E" to internal patient_id
query = """
SELECT p.patient_id
FROM patient p
JOIN patient_identifier pi ON p.patient_id = pi.patient_id
WHERE pi.identifier = '100008E'
LIMIT 1
"""

result = db.execute_query(query)
if result['data']:
    patient_id_internal = result['data'][0]['patient_id']
    print(f"Resolved 100008E to internal patient_id: {patient_id_internal}")
    
    # Now test the vitals history query with the corrected limit and internal ID
    vitals_result = db.get_patient_vitals_history(patient_id_internal, limit=100)
    
    print(f"\nVitals result type: {type(vitals_result)}")
    print(f"Vitals result keys: {vitals_result.keys() if isinstance(vitals_result, dict) else 'Not a dict'}")
    
    vitals_data = vitals_result.get("data", []) if isinstance(vitals_result, dict) else vitals_result
    print(f"Total vitals records retrieved: {len(vitals_data)}")
    
    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for v in vitals_data:
        date_key = v['obs_datetime']
        by_date[date_key].append(v)
    
    print(f"Number of different dates: {len(by_date)}")
    for date_key in sorted(by_date.keys(), reverse=True):
        print(f"  {date_key}: {len(by_date[date_key])} records")
