#!/usr/bin/env python3
"""Check all observations for patient"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

# First, find the person_id for patient 100008
query1 = """
SELECT p.patient_id
FROM patient p
WHERE p.patient_id = 100008
"""

result1 = db.execute_query(query1)
if result1['error']:
    print(f"Error finding patient: {result1['error']}")
else:
    patient_data = result1['data']
    if patient_data:
        patient_id = patient_data[0]['patient_id']
        # In OpenMRS, patient_id = person_id for patients
        person_id = patient_id
        print(f"Patient ID: {patient_id} (Person ID: {person_id})\n")
        
        # Now check observations with this person_id
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
        
        result2 = db.execute_query(query2, (person_id,))
        if result2['error']:
            print(f"Error: {result2['error']}")
        else:
            print("All observations (top 30):")
            for v in result2['data']:
                print(f"  {v['vital_name']}: {v['count']}")
    else:
        print("Patient 100008 not found")
