#!/usr/bin/env python3
"""Get all vitals for patient without limit"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

# Get vitals data for patient 100008E (patient_id=15)
query = """
SELECT cn.name as vital_name, o.value_numeric, o.value_text, o.obs_datetime
FROM obs o
JOIN concept_name cn ON o.concept_id = cn.concept_id
WHERE o.person_id = %s
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
ORDER BY o.obs_datetime DESC
"""

result = db.execute_query(query, (15,))
print(f"Total vitals found: {len(result['data'])}")
print("\nAll vitals (by date):")
for v in result['data']:
    value = v['value_numeric'] or v['value_text']
    print(f"  {v['obs_datetime']}: {v['vital_name']} = {value}")
