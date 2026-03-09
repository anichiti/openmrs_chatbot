import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()
db.connect()
cursor = db.connection.cursor()

# Get immunization observations for patient 15
print("=" * 80)
print("CHECKING IMMUNIZATION DATA IN OPENMRS FOR PATIENT 100008E (ID: 15)")
print("=" * 80)

query = '''
SELECT 
    o.obs_id,
    o.obs_datetime,
    cn.name as concept_name,
    o.value_text,
    o.value_coded,
    o.value_numeric,
    o.value_datetime
FROM obs o
JOIN concept c ON o.concept_id = c.CONCEPT_ID
JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
WHERE o.person_id = 15
AND o.voided = 0
LIMIT 30
'''

cursor.execute(query)
results = cursor.fetchall()

print("\nAll Observations for Patient 15:")
print("-" * 80)
for row in results:
    print(f"Obs ID: {row[0]}, DateTime: {row[1]}")
    print(f"  Concept: {row[2]}")
    print(f"  Value Text: {row[3]}")
    print(f"  Value Coded: {row[4]}")
    print(f"  Value Numeric: {row[5]}")
    print(f"  Value DateTime: {row[6]}")
    print()

# Look for vaccine-related observations
print("\n" + "=" * 80)
print("SEARCHING FOR VACCINE-RELATED OBSERVATIONS")
print("=" * 80)

query2 = '''
SELECT DISTINCT cn.name
FROM obs o
JOIN concept c ON o.concept_id = c.CONCEPT_ID
JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
WHERE cn.name LIKE '%vaccin%' OR cn.name LIKE '%immun%'
LIMIT 50
'''

cursor.execute(query2)
vaccine_concepts = cursor.fetchall()
print(f"\nFound {len(vaccine_concepts)} vaccine-related concept names:")
for row in vaccine_concepts:
    print(f"  - {row[0]}")

# Check if there are obs_group entries for vaccines
print("\n" + "=" * 80)
print("CHECKING OBS_GROUP ENTRIES (hierarchical observations)")
print("=" * 80)

query3 = '''
SELECT 
    o.obs_id,
    o.obs_datetime,
    cn.name as parent_concept,
    o.value_coded,
    o.obs_group_id
FROM obs o
JOIN concept c ON o.concept_id = c.CONCEPT_ID
JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
WHERE o.person_id = 15
AND o.obs_group_id IS NOT NULL
AND o.voided = 0
LIMIT 20
'''

cursor.execute(query3)
group_results = cursor.fetchall()
print(f"\nFound {len(group_results)} grouped observations:")
for row in group_results:
    print(f"Obs ID: {row[0]}, DateTime: {row[1]}, Parent: {row[2]}, Value Coded: {row[3]}, Group ID: {row[4]}")

db.connection.close()
print("\n" + "=" * 80)
