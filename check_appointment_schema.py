#!/usr/bin/env python3
"""Check patient_appointment table schema"""
import sys
sys.path.insert(0, 'c:/Users/chiti/Downloads/openmrs_chatbot/openmrs_chatbot')

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()

if db.connect():
    cursor = db.connection.cursor()
    
    print("=" * 80)
    print("PATIENT_APPOINTMENT TABLE STRUCTURE")
    print("=" * 80 + "\n")
    
    cursor.execute("DESCRIBE patient_appointment")
    columns = cursor.fetchall()
    
    print("Columns:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")
    
    print("\n" + "=" * 80)
    print("SAMPLE DATA FROM PATIENT_APPOINTMENT")
    print("=" * 80 + "\n")
    
    # Get sample records
    cursor.execute("""
        SELECT * FROM patient_appointment 
        WHERE patient_id = 15 AND voided = 0
        LIMIT 5
    """)
    
    records = cursor.fetchall()
    if records:
        print(f"Found {len(records)} appointments:\n")
        for i, record in enumerate(records, 1):
            print(f"{i}. {record}")
    else:
        print("No appointments found for patient 15")
    
    cursor.close()
    db.disconnect()
else:
    print("Failed to connect to database")
