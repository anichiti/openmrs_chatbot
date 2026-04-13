#!/usr/bin/env python3
"""Check vitals data in database"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

# Check how many vitals records exist for patient 100008
query = """
SELECT cn.name as vital_name, COUNT(*) as count
FROM obs o
JOIN concept_name cn ON o.concept_id = cn.concept_id
WHERE o.person_id = 100008
AND o.voided = false
AND cn.name IN ('Height (cm)', 'Weight (kg)', 'Systolic Blood Pressure', 
                'Diastolic Blood Pressure', 'Temperature (C)', 'Blood Pressure',
                'Height', 'Weight', 'BP', 'Temp', 'BMI', 'Body Mass Index',
                'Body mass index', 'BMI (kg/m2)', 'BMI (kg/m²)',
                'Pulse', 'Heart Rate', 'Heart rate', 'Pulse Rate',
                'Respiratory Rate', 'Respiratory rate', 'Respiration Rate',
                'Blood Oxygen Saturation', 'Oxygen Saturation', 'SpO2',
                'Arterial blood oxygen saturation (pulse oximeter)',
                'Head Circumference', 'Head circumference (cm)',
                'Mid-Upper Arm Circumference', 'MUAC')
GROUP BY cn.name
ORDER BY count DESC
"""

result = db.execute_query(query)
if result['error']:
    print(f"Error: {result['error']}")
else:
    vitals_data = result['data']
    print(f"Total vital types with records: {len(vitals_data)}")
    print("\nVitals by type:")
    for v in vitals_data:
        print(f"  {v['vital_name']}: {v['count']} records")
