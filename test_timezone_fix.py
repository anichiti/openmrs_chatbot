#!/usr/bin/env python
import sys
sys.path.insert(0, 'openmrs_chatbot')

from openmrs_chatbot.database.db import OpenMRSDatabase

db = OpenMRSDatabase()
db.connect()

print("=" * 80)
print("TESTING ENCOUNTERS WITH TIMEZONE CORRECTION (4-hour offset)")
print("=" * 80)

result = db.get_patient_encounters(15, limit=5)
if result['error'] is None and result['data']:
    print(f"\nRetrieved {len(result['data'])} encounters with timezone offset applied:\n")
    for i, enc in enumerate(result['data'], 1):
        print(f"{i}. Encounter ID: {enc['encounter_id']}")
        print(f"   Type: {enc['encounter_type_name']}")
        print(f"   Date/Time: {enc['encounter_datetime']}")
        print()
else:
    print(f"Error: {result['error']}")

print("=" * 80)
print("TESTING APPOINTMENTS WITH TIMEZONE CORRECTION")
print("=" * 80)

result = db.get_patient_appointments(15)
if result['error'] is None and result['data']:
    print(f"\nRetrieved {len(result['data'])} appointments with timezone offset:\n")
    for i, appt in enumerate(result['data'], 1):
        print(f"{i}. Appointment ID: {appt['patient_appointment_id']}")
        print(f"   Start: {appt['start_date_time']}")
        print(f"   Service: {appt['service_name']}")
        print()
else:
    print(f"Error: {result['error']}")

print("=" * 80)
print("TESTING FUTURE APPOINTMENTS")
print("=" * 80)

result = db.get_patient_appointments_future(15)
if result['error'] is None and result['data']:
    print(f"\nRetrieved {len(result['data'])} future appointments:\n")
    for i, appt in enumerate(result['data'], 1):
        print(f"{i}. Appointment ID: {appt['patient_appointment_id']}")
        print(f"   Start: {appt['start_date_time']}")
        print(f"   Service: {appt['service_name']}")
        print()
else:
    print(f"No future appointments found or error: {result['error']}")

db.disconnect()
