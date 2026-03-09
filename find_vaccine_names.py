#!/usr/bin/env python3
"""Find actual vaccine names in OpenMRS database"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from database.db import OpenMRSDatabase

try:
    db_handler = OpenMRSDatabase()
    db_handler.connect()
    db = db_handler.connection
    cursor = db.cursor()
    
    print("\n" + "=" * 80)
    print("FINDING ACTUAL VACCINE NAMES")
    print("=" * 80)
    
    # First, let's find what vaccine value the immunization obs_group records have
    # by looking at the parent observation that links to the group
    
    query1 = '''
    SELECT DISTINCT
        c.CONCEPT_ID,
        cn.name as concept_name,
        COUNT(*) as count
    FROM obs o
    LEFT JOIN concept c ON o.concept_id = c.CONCEPT_ID
    LEFT JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
    WHERE o.person_id = 15
    AND o.obs_group_id IS NULL  -- Parent observations only
    AND cn.name IN ('Immunizations', 'Immunisation', 'Vaccination', 'Vaccine', 'IMMUNIZATIONS', 'Immunizations given')
    AND o.voided = 0
    GROUP BY c.CONCEPT_ID, cn.name
    '''
    
    cursor.execute(query1)
    results = cursor.fetchall()
    
    print("\nParent Immunizations concepts (obs_group_id IS NULL):")
    print("-" * 80)
    for row in results:
        print(f"Concept ID: {row[0]}, Name: {row[1]}, Count: {row[2]}")
    
    print("\n" + "=" * 80)
    print("LOOKING FOR VACCINE NAMES IN VALUE_CODED")
    print("=" * 80)
    
    # Now let's look at what value_coded values appear in immunization obs_group records
    query2 = '''
    SELECT DISTINCT
        o.value_coded,
        c.CONCEPT_ID,
        cn.name as vaccine_name,
        COUNT(*) as count
    FROM obs o
    LEFT JOIN obs parent_o ON o.obs_group_id = parent_o.obs_id
    LEFT JOIN concept c ON o.value_coded = c.CONCEPT_ID
    LEFT JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
    WHERE o.person_id = 15
    AND o.obs_group_id IS NOT NULL
    AND o.value_coded IS NOT NULL
    AND o.voided = 0
    GROUP BY o.value_coded, c.CONCEPT_ID, cn.name
    ORDER BY count DESC
    '''
    
    cursor.execute(query2)
    results = cursor.fetchall()
    
    print("\nVaccine names from value_coded fields in grouped observations:")
    print("-" * 80)
    for row in results:
        print(f"Value Coded: {row[0]}, Concept ID: {row[1]}, Name: {row[2]}, Count: {row[3]}")
    
    print("\n" + "=" * 80)
    print("CHECKING IMMUNIZATION PARENT OBS STRUCTURE")
    print("=" * 80)
    
    # Check what the parent obs records look like for immunizations
    query3 = '''
    SELECT 
        o.obs_id,
        o.obs_group_id,
        o.concept_id,
        cn.name,
        o.value_coded,
        o.value_text,
        o.obs_datetime
    FROM obs o
    LEFT JOIN concept_name cn ON o.concept_id = cn.CONCEPT_ID
    WHERE o.person_id = 15
    AND o.obs_group_id IS NULL
    AND cn.name = 'Immunizations'
    AND o.voided = 0
    LIMIT 5
    '''
    
    cursor.execute(query3)
    results = cursor.fetchall()
    
    print("\nParent Immunizations observations:")
    print("-" * 80)
    for row in results:
        print(f"Obs ID: {row[0]}, Group ID: {row[1]}")
        print(f"  Concept ID/Name: {row[2]} / {row[3]}")
        print(f"  Value Coded: {row[4]}")
        print(f"  Value Text: {row[5]}")
        print(f"  DateTime: {row[6]}")
        print()
    
    cursor.close()
    db_handler.disconnect()
    print("\n✓ Investigation complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
