#!/usr/bin/env python3
"""Check database schema for appointment-related tables"""
import sys
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

if db.connect():
    print("=" * 80)
    print("CHECKING DATABASE SCHEMA FOR APPOINTMENT-RELATED TABLES")
    print("=" * 80)
    
    cursor = db.connection.cursor()
    
    # Get all tables in the database
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print("\nAll tables in database:\n")
    appointment_tables = []
    for table in tables:
        table_name = table[0]
        if 'appoint' in table_name.lower() or 'visit' in table_name.lower() or 'encounter' in table_name.lower():
            appointment_tables.append(table_name)
            print(f"  * {table_name} (RELEVANT)")
        else:
            print(f"    {table_name}")
    
    # Check visit table schema if it exists
    print("\n" + "=" * 80)
    print("VISIT TABLE SCHEMA")
    print("=" * 80)
    
    try:
        cursor.execute("DESCRIBE visit")
        visit_schema = cursor.fetchall()
        print("\nVisit table columns:")
        for col in visit_schema:
            print(f"  - {col[0]}: {col[1]}")
    except Exception as e:
        print(f"Could not get visit schema: {e}")
    
    # Query for visits (future and past)
    print("\n" + "=" * 80)
    print("CHECKING VISIT TABLE FOR PATIENT 15")
    print("=" * 80)
    
    try:
        visit_query = """
            SELECT v.visit_id, v.patient_id, v.visit_type_id, v.date_started, v.date_stopped, 
                   vt.name as visit_type_name
            FROM visit v
            LEFT JOIN visit_type vt ON v.visit_type_id = vt.visit_type_id
            WHERE v.patient_id = %s AND v.voided = 0
            ORDER BY v.date_started DESC
            LIMIT 20
        """
        
        cursor.execute(visit_query, (15,))
        visits = cursor.fetchall()
        
        if visits:
            print(f"\nTotal Visits Found: {len(visits)}\n")
            for i, visit in enumerate(visits, 1):
                print(f"{i}. Visit ID: {visit[0]}")
                print(f"   Patient ID: {visit[1]}")
                print(f"   Visit Type ID: {visit[2]}")
                print(f"   Started: {visit[3]}")
                print(f"   Stopped: {visit[4]}")
                print(f"   Visit Type: {visit[5]}")
                print()
        else:
            print("No visits found")
    except Exception as e:
        print(f"Could not query visits: {e}")
    
    cursor.close()
    db.disconnect()
else:
    print("Failed to connect to database")

print("=" * 80)
