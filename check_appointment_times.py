#!/usr/bin/env python
import sys
sys.path.insert(0, 'openmrs_chatbot')

from openmrs_chatbot.database.db import OpenMRSDatabase

db = OpenMRSDatabase()
db.connect()

query = '''
    SELECT patient_appointment_id, start_date_time, end_date_time
    FROM patient_appointment
    WHERE patient_id = 15 
    ORDER BY patient_appointment_id
'''

result = db.execute_query(query)
if result['error'] is None and result['data']:
    print("\n=== DATABASE APPOINTMENT TIMES ===\n")
    for row in result['data']:
        print(f"Appointment ID: {row['patient_appointment_id']}")
        print(f"  Start Time: {row['start_date_time']}")
        print(f"  End Time: {row['end_date_time']}")
        print()
else:
    print(f"Error: {result['error']}")

db.disconnect()
