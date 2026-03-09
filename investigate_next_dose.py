#!/usr/bin/env python3
"""Investigate next dose scheduling in OpenMRS database"""

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
    print("NEXT DOSE SCHEDULING INVESTIGATION")
    print("=" * 80)
    
    # Look for "Date of next dose" observations in obs_group
    query = '''
    SELECT DISTINCT
        parent_o.obs_id as group_obs_id,
        parent_o.obs_datetime as group_date,
        vaccine_cn.name as vaccine_name,
        next_dose_o.obs_id as next_dose_obs_id,
        next_dose_o.value_datetime,
        next_dose_o.value_text,
        next_dose_c.CONCEPT_ID,
        next_dose_cn.name as next_dose_concept
    FROM obs parent_o
    JOIN obs vac_o ON vac_o.obs_group_id = parent_o.obs_id
    JOIN concept vac_c ON vac_o.concept_id = vac_c.CONCEPT_ID
    JOIN concept_name vac_concept_cn ON vac_c.CONCEPT_ID = vac_concept_cn.CONCEPT_ID
    JOIN concept vaccine_concept ON vac_o.value_coded = vaccine_concept.CONCEPT_ID
    JOIN concept_name vaccine_cn ON vaccine_concept.CONCEPT_ID = vaccine_cn.CONCEPT_ID
    LEFT JOIN obs next_dose_o ON next_dose_o.obs_group_id = parent_o.obs_id
    LEFT JOIN concept next_dose_c ON next_dose_o.concept_id = next_dose_c.CONCEPT_ID
    LEFT JOIN concept_name next_dose_cn ON next_dose_c.CONCEPT_ID = next_dose_cn.CONCEPT_ID
    WHERE parent_o.person_id = 15
    AND vac_concept_cn.name IN ('Immunizations', 'Immunisation', 'Vaccination', 'IMMUNIZATIONS')
    AND parent_o.voided = 0
    AND vac_o.voided = 0
    AND vaccine_cn.concept_name_type = 'FULLY_SPECIFIED'
    ORDER BY parent_o.obs_datetime DESC, next_dose_cn.name
    LIMIT 50
    '''
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"\nFound {len(results)} observations with next dose info:")
    print("-" * 80)
    
    current_group = None
    for row in results:
        group_id, group_date, vaccine_name, next_obs_id, next_date, next_text, concept_id, next_concept = row
        
        if group_id != current_group:
            print(f"\nGroup {group_id} - Date: {group_date}, Vaccine: {vaccine_name}")
            current_group = group_id
        
        if next_concept:
            print(f"  > {next_concept}")
            if next_date:
                print(f"    Value (datetime): {next_date}")
            if next_text:
                print(f"    Value (text): {next_text}")
    
    print("\n" + "=" * 80)
    print("CHECKING FOR SPECIFIC NEXT DOSE CONCEPTS")
    print("=" * 80)
    
    # Find all unique concepts related to next dose
    query2 = '''
    SELECT DISTINCT
        cn.name,
        COUNT(*) as count
    FROM obs parent_o
    JOIN obs child_o ON child_o.obs_group_id = parent_o.obs_id
    JOIN concept c ON child_o.concept_id = c.CONCEPT_ID
    JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
    WHERE parent_o.person_id = 15
    AND (cn.name LIKE '%next%' OR cn.name LIKE '%scheduled%' OR cn.name LIKE '%date%')
    AND parent_o.voided = 0
    AND child_o.voided = 0
    GROUP BY cn.name
    ORDER BY count DESC
    '''
    
    cursor.execute(query2)
    results2 = cursor.fetchall()
    
    print("\nConcept names related to 'next', 'scheduled', 'date':")
    print("-" * 80)
    for name, count in results2:
        print(f"{name}: {count} occurrences")
    
    cursor.close()
    db_handler.disconnect()
    print("\n✓ Investigation complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
