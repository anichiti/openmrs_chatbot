#!/usr/bin/env python3
"""Get future scheduled appointments - correct query"""
import sys
from datetime import datetime
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

if db.connect():
    cursor = db.connection.cursor(dictionary=True)
    
    print("=" * 80)
    print("FUTURE SCHEDULED APPOINTMENTS FOR PATIENT 100008E (JOSHUA JOHNSON)")
    print("=" * 80)
    print(f"\nCurrent Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Query for future appointments (subtract 4 hours for timezone offset)
    future_query = """
        SELECT pa.patient_appointment_id, pa.provider_id, pa.appointment_number,
               DATE_SUB(pa.start_date_time, INTERVAL 4 HOUR) as start_date_time,
               DATE_SUB(pa.end_date_time, INTERVAL 4 HOUR) as end_date_time,
               pa.status, pa.appointment_kind,
               pa.location_id, pa.comments, appt_service.name as service_name
        FROM patient_appointment pa
        LEFT JOIN appointment_service appt_service ON pa.appointment_service_id = appt_service.appointment_service_id
        WHERE pa.patient_id = %s 
        AND pa.voided = 0
        AND pa.start_date_time > NOW()
        ORDER BY pa.start_date_time ASC
    """
    
    cursor.execute(future_query, (15,))
    future_appointments = cursor.fetchall()
    
    print("\n" + "=" * 80)
    print("FUTURE SCHEDULED APPOINTMENTS (AFTER TODAY)")
    print("=" * 80)
    
    if future_appointments:
        print(f"\nTotal Future Appointments: {len(future_appointments)}\n")
        for i, appt in enumerate(future_appointments, 1):
            print(f"{i}. Appointment ID: {appt['patient_appointment_id']}")
            print(f"   Appointment #: {appt['appointment_number']}")
            print(f"   Start Date/Time: {appt['start_date_time']}")
            print(f"   End Date/Time: {appt['end_date_time']}")
            print(f"   Status: {appt['status']}")
            print(f"   Service: {appt['service_name']}")
            print(f"   Type: {appt['appointment_kind']}")
            print(f"   Location ID: {appt['location_id']}")
            print(f"   Comments: {appt['comments']}")
            print()
    else:
        print("\nNo future appointments scheduled.")
    
    # Get ALL appointments
    print("\n" + "=" * 80)
    print("ALL APPOINTMENTS (PAST & FUTURE)")
    print("=" * 80)
    
    all_query = """
        SELECT pa.patient_appointment_id, pa.provider_id, pa.appointment_number,
               DATE_SUB(pa.start_date_time, INTERVAL 4 HOUR) as start_date_time,
               DATE_SUB(pa.end_date_time, INTERVAL 4 HOUR) as end_date_time,
               pa.status, pa.appointment_kind,
               pa.location_id, pa.comments, appt_service.name as service_name
        FROM patient_appointment pa
        LEFT JOIN appointment_service appt_service ON pa.appointment_service_id = appt_service.appointment_service_id
        WHERE pa.patient_id = %s 
        AND pa.voided = 0
        ORDER BY pa.start_date_time DESC
    """
    
    cursor.execute(all_query, (15,))
    all_appointments = cursor.fetchall()
    
    if all_appointments:
        print(f"\nTotal Appointments: {len(all_appointments)}\n")
        for i, appt in enumerate(all_appointments, 1):
            is_future = appt['start_date_time'] > datetime.now()
            status_label = "[FUTURE]" if is_future else "[PAST]"
            
            print(f"{i}. {status_label} Appointment ID: {appt['patient_appointment_id']}")
            print(f"   Start: {appt['start_date_time']}")
            print(f"   End: {appt['end_date_time']}")
            print(f"   Status: {appt['status']}")
            print(f"   Service: {appt['service_name']}")
            print(f"   Type: {appt['appointment_kind']}")
            print()
    else:
        print("\nNo appointments found.")
    
    cursor.close()
    db.disconnect()
else:
    print("Failed to connect to database")

print("=" * 80)
