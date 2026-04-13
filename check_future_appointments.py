#!/usr/bin/env python3
"""Get future scheduled appointments from patient_appointment table"""
import sys
from datetime import datetime
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

if db.connect():
    print("=" * 80)
    print("FUTURE SCHEDULED APPOINTMENTS FOR PATIENT 100008E (JOSHUA JOHNSON)")
    print("=" * 80)
    print(f"\nCurrent Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    cursor = db.connection.cursor(dictionary=True)
    
    # Query future appointments
    future_appt_query = """
        SELECT pa.patient_appointment_id, pa.patient_id, pa.appointment_date, 
               pa.appointment_start_time, pa.appointment_end_time, 
               pa.status, pa.notes, pa.appointment_kind,
               appt_service.name as service_name, appt_spec.name as speciality_name
        FROM patient_appointment pa
        LEFT JOIN appointment_service appt_service ON pa.appointment_service_id = appt_service.appointment_service_id
        LEFT JOIN appointment_speciality appt_spec ON pa.appointment_speciality_id = appt_spec.appointment_speciality_id
        WHERE pa.patient_id = %s 
        AND pa.voided = 0
        AND (
            CONCAT(pa.appointment_date, ' ', pa.appointment_start_time) > NOW()
            OR (pa.appointment_date >= CURDATE() AND pa.appointment_date IS NOT NULL)
        )
        ORDER BY pa.appointment_date ASC, pa.appointment_start_time ASC
        LIMIT 50
    """
    
    cursor.execute(future_appt_query, (15,))
    future_appointments = cursor.fetchall()
    
    print("\n" + "=" * 80)
    print("FUTURE SCHEDULED APPOINTMENTS")
    print("=" * 80)
    
    if future_appointments:
        print(f"\nTotal Future Appointments: {len(future_appointments)}\n")
        for i, appt in enumerate(future_appointments, 1):
            print(f"{i}. Appointment ID: {appt['patient_appointment_id']}")
            print(f"   Date: {appt['appointment_date']}")
            print(f"   Time: {appt['appointment_start_time']} - {appt['appointment_end_time']}")
            print(f"   Status: {appt['status']}")
            print(f"   Service: {appt['service_name']}")
            print(f"   Specialty: {appt['speciality_name']}")
            print(f"   Type: {appt['appointment_kind']}")
            print(f"   Notes: {appt['notes']}")
            print()
    else:
        print("\nNo future appointments found.")
    
    # Also get ALL appointments (past and future)
    print("\n" + "=" * 80)
    print("ALL SCHEDULED APPOINTMENTS (PAST AND FUTURE)")
    print("=" * 80)
    
    all_appt_query = """
        SELECT pa.patient_appointment_id, pa.patient_id, pa.appointment_date, 
               pa.appointment_start_time, pa.appointment_end_time, 
               pa.status, pa.notes, pa.appointment_kind,
               appt_service.name as service_name, appt_spec.name as speciality_name
        FROM patient_appointment pa
        LEFT JOIN appointment_service appt_service ON pa.appointment_service_id = appt_service.appointment_service_id
        LEFT JOIN appointment_speciality appt_spec ON pa.appointment_speciality_id = appt_spec.appointment_speciality_id
        WHERE pa.patient_id = %s 
        AND pa.voided = 0
        ORDER BY pa.appointment_date DESC, pa.appointment_start_time DESC
        LIMIT 50
    """
    
    cursor.execute(all_appt_query, (15,))
    all_appointments = cursor.fetchall()
    
    if all_appointments:
        print(f"\nTotal Appointments (All): {len(all_appointments)}\n")
        for i, appt in enumerate(all_appointments, 1):
            appt_date = appt['appointment_date']
            appt_time = appt['appointment_start_time']
            is_future = False
            
            try:
                appt_datetime = datetime.combine(appt_date, appt_time)
                is_future = appt_datetime > datetime.now()
            except:
                pass
            
            status_label = "[FUTURE]" if is_future else "[PAST]"
            
            print(f"{i}. {status_label} Appointment ID: {appt['patient_appointment_id']}")
            print(f"   Date: {appt['appointment_date']}")
            print(f"   Time: {appt['appointment_start_time']} - {appt['appointment_end_time']}")
            print(f"   Status: {appt['status']}")
            print(f"   Service: {appt['service_name']}")
            print(f"   Specialty: {appt['speciality_name']}")
            print(f"   Type: {appt['appointment_kind']}")
            print()
    else:
        print("\nNo appointments found in database.")
    
    cursor.close()
    db.disconnect()
else:
    print("Failed to connect to database")

print("=" * 80)
