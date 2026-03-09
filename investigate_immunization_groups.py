import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()
db.connect()
cursor = db.connection.cursor()

print("=" * 80)
print("DETAILED IMMUNIZATIONS QUERY FOR PATIENT 100008E")
print("=" * 80)

# Query for Immunizations observations with their value
query = '''
SELECT 
    o.obs_id,
    o.obs_datetime,
    cn.name as concept_name,
    o.value_text,
    o.value_coded,
    o.obs_group_id
FROM obs o
LEFT JOIN concept c ON o.concept_id = c.CONCEPT_ID
LEFT JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
WHERE o.person_id = 15
AND (cn.name IN ('Immunizations', 'Immunization Hx', 'Immunizations given', 'Vaccination date', 'Immunization date'))
AND o.voided = 0
ORDER BY o.obs_datetime DESC
'''

cursor.execute(query)
results = cursor.fetchall()

print(f"\nFound {len(results)} immunization-related observations:")
print("-" * 80)
for row in results:
    print(f"Obs ID: {row[0]}, DateTime: {row[1]}")
    print(f"  Concept: {row[2]}")
    print(f"  Value Text: {row[3]}")
    print(f"  Value Coded: {row[4]}")
    print(f"  Group ID: {row[5]}")
    print()

# Now let's get the group observations (children) for these immunization records
print("\n" + "=" * 80)
print("IMMUNIZATION OBSERVATION GROUPS (Child observations)")
print("=" * 80)

query2 = '''
SELECT 
    o.obs_id,
    o.obs_group_id,
    cn.name as concept_name,
    o.value_text,
    o.value_coded,
    o.value_numeric,
    o.obs_datetime
FROM obs o
LEFT JOIN concept c ON o.concept_id = c.CONCEPT_ID
LEFT JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
WHERE o.person_id = 15
AND o.obs_group_id IS NOT NULL
AND o.voided = 0
ORDER BY o.obs_group_id, o.obs_id
'''

cursor.execute(query2)
group_results = cursor.fetchall()

print(f"\nFound {len(group_results)} grouped child observations:")
print("-" * 80)
for row in group_results:
    print(f"Obs ID: {row[0]}, Group ID: {row[1]}")
    print(f"  Concept: {row[2]}")
    print(f"  Value Text: {row[3]}")
    print(f"  Value Coded: {row[4]}")
    print(f"  Value Numeric: {row[5]}")
    print(f"  DateTime: {row[6]}")
    print()

db.connection.close()
print("=" * 80)
