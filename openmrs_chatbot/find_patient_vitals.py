#!/usr/bin/env python3
"""List all patients and find vitals"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

# Search by identifier (100008E from the UI)
query1 = """
SELECT p.patient_id, pi.identifier
FROM patient p
JOIN patient_identifier pi ON p.patient_id = pi.patient_id
WHERE pi.identifier = '100008E'
LIMIT 1
"""

result1 = db.execute_query(query1)
print(f"Search result: {result1}")

if result1['data']:
    patient_id = result1['data'][0]['patient_id']
    print(f"\nFound patient ID: {patient_id}")
    
    # Now get all observations
    query2 = """
    SELECT cn.name as vital_name, COUNT(*) as count
    FROM obs o
    JOIN concept_name cn ON o.concept_id = cn.concept_id
    WHERE o.person_id = %s
    AND o.voided = false
    GROUP BY cn.name
    ORDER BY count DESC
    LIMIT 30
    """
    
    result2 = db.execute_query(query2, (patient_id,))
    if result2['data']:
        print("\nObservations for patient:")
        for v in result2['data']:
            print(f"  {v['vital_name']}: {v['count']}")
