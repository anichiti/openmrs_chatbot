#!/usr/bin/env python3
"""Get future scheduled appointments"""
import sys
from datetime import datetime
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from database.db import OpenMRSDatabase

print("=" * 80)
print("FUTURE SCHEDULED APPOINTMENTS FOR PATIENT 100008E (JOSHUA JOHNSON)")
print("=" * 80)

db = OpenMRSDatabase()

# Connect and get patient info first
if db.connect():
    # Get internal patient ID
    patient_query = "SELECT patient_id FROM patient WHERE patient_id = %s AND voided = false"
    cursor = db.connection.cursor(dictionary=True)
    cursor.execute(patient_query, (15,))  # 15 is internal ID
    patient_result = cursor.fetchone()
    
    if patient_result:
        patient_id = patient_result['patient_id']
        print(f"\nPatient ID (Internal): {patient_id}")
        print(f"Current Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Query for future scheduled appointments/encounters
        # Check the appointment table if it exists, or use encounter table
        future_query = """
            SELECT e.encounter_id, e.patient_id, e.encounter_type, e.encounter_datetime,
                   e.location_id, et.name as encounter_type_name
            FROM encounter e
            LEFT JOIN encounter_type et ON e.encounter_type = et.encounter_type_id
            WHERE e.patient_id = %s 
            AND e.voided = false
            AND e.encounter_datetime > NOW()
            ORDER BY e.encounter_datetime ASC
            LIMIT 100
        """
        
        cursor.execute(future_query, (patient_id,))
        future_appointments = cursor.fetchall()
        
        print("\n" + "=" * 80)
        print("FUTURE APPOINTMENTS/ENCOUNTERS")
        print("=" * 80)
        
        if future_appointments:
            print(f"\nTotal Future Appointments: {len(future_appointments)}\n")
            for i, appt in enumerate(future_appointments, 1):
                print(f"{i}. Encounter ID: {appt['encounter_id']}")
                print(f"   Date/Time: {appt['encounter_datetime']}")
                print(f"   Type: {appt['encounter_type_name']}")
                print(f"   Location: {appt['location_id']}")
                print()
        else:
            print("\nNo future appointments found in database.")
            print("(Current date is April 12, 2026)")
        
        # Also check if there's an appointment table
        print("\n" + "=" * 80)
        print("CHECKING FOR APPOINTMENT TABLE")
        print("=" * 80)
        
        try:
            appt_query = """
                SELECT a.appointment_id, a.patient_id, a.appointment_type, 
                       a.scheduled_date_time, a.status, a.location_id
                FROM appointments a
                WHERE a.patient_id = %s 
                AND a.status IN ('scheduled', 'pending')
                AND a.scheduled_date_time > NOW()
                ORDER BY a.scheduled_date_time ASC
                LIMIT 100
            """
            
            cursor.execute(appt_query, (patient_id,))
            appointments = cursor.fetchall()
            
            if appointments:
                print(f"\nTotal Scheduled Appointments: {len(appointments)}\n")
                for i, appt in enumerate(appointments, 1):
                    print(f"{i}. Appointment ID: {appt['appointment_id']}")
                    print(f"   Scheduled Date/Time: {appt['scheduled_date_time']}")
                    print(f"   Type: {appt['appointment_type']}")
                    print(f"   Status: {appt['status']}")
                    print(f"   Location: {appt['location_id']}")
                    print()
            else:
                print("No appointments found in appointments table")
        except Exception as e:
            print(f"Appointments table query failed: {e}")
            print("(Table may not exist in this OpenMRS instance)")
        
        cursor.close()
    
    db.disconnect()
else:
    print("Failed to connect to database")

print("\n" + "=" * 80)
