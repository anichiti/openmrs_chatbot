#!/usr/bin/env python3
"""Get encounters and visits for patient"""
import sys
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from database.db import OpenMRSDatabase

print("=" * 80)
print("RETRIEVING ENCOUNTERS AND VISITS FOR PATIENT 100008E (JOSHUA JOHNSON)")
print("=" * 80)

# Connect to database
db = OpenMRSDatabase()

# Get patient info
print("\n1. PATIENT INFORMATION:")
print("-" * 80)
patient = db.get_patient_by_id("100008E")
if patient.get('data'):
    p = patient['data'][0]
    print(f"Name: {p.get('given_name')} {p.get('family_name')}")
    print(f"Patient ID (External): {p.get('patient_identifier')}")
    print(f"Patient ID (Internal): {p.get('patient_id')}")
    print(f"Gender: {p.get('gender')}")
    print(f"DOB: {p.get('birthdate')}")

# Get encounters
print("\n2. ENCOUNTERS:")
print("-" * 80)
encounters = db.get_patient_encounters("100008E", limit=100)
if encounters.get('data'):
    print(f"Total Encounters: {len(encounters['data'])}\n")
    for i, enc in enumerate(encounters['data'], 1):
        print(f"{i}. ID: {enc.get('encounter_id')}")
        print(f"   Date/Time: {enc.get('encounter_datetime')}")
        print(f"   Type: {enc.get('encounter_type_name')}")
        print(f"   Location: {enc.get('location_id')}")
        print()

# Try to get visits
print("\n3. VISITS (if separate table exists):")
print("-" * 80)
try:
    # Try direct SQL query for visits
    query = """
        SELECT DISTINCT v.visit_id, v.patient_id, v.visit_type_id, v.date_started, v.date_stopped, vt.name as visit_type_name
        FROM visit v
        LEFT JOIN visit_type vt ON v.visit_type_id = vt.visit_type_id
        WHERE v.patient_id = %s AND v.voided = 0
        ORDER BY v.date_started DESC
        LIMIT 100
    """
    
    conn = db.connect()
    if conn:
        cursor = conn.cursor()
        cursor.execute(query, (15,))  # Internal patient ID is 15
        visits = cursor.fetchall()
        
        if visits:
            print(f"Total Visits: {len(visits)}\n")
            for i, visit in enumerate(visits, 1):
                print(f"{i}. Visit ID: {visit[0]}")
                print(f"   Patient ID: {visit[1]}")
                print(f"   Type ID: {visit[2]}")
                print(f"   Started: {visit[3]}")
                print(f"   Stopped: {visit[4]}")
                print(f"   Visit Type: {visit[5]}")
                print()
        else:
            print("No visits found in database")
        
        cursor.close()
        conn.close()
except Exception as e:
    print(f"Could not retrieve visits: {e}")

print("-" * 80)
