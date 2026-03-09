import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()
db.connect()

# Get all tables
cursor = db.connection.cursor()
cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'openmrs' ORDER BY TABLE_NAME")
tables = [row[0] for row in cursor.fetchall()]

print("Available OpenMRS Tables:")
print("=" * 60)
for table in tables:
    print(table)

# Look for immunization-related tables
print("\n" + "=" * 60)
print("Immunization-related tables:")
print("=" * 60)
immune_tables = [t for t in tables if 'immun' in t.lower() or 'vaccin' in t.lower()]
print(f"Found: {immune_tables if immune_tables else 'None - immunization stored in obs/program tables'}")

# Show patient_program table structure
print("\n" + "=" * 60)
print("Patient Program Fields:")
print("=" * 60)
cursor.execute("DESCRIBE patient_program")
for row in cursor.fetchall():
    print(f"  {row[0]:30} {row[1]}")

# Show obs table structure
print("\n" + "=" * 60)
print("Observations (obs) Fields:")
print("=" * 60)
cursor.execute("DESCRIBE obs")
fields = cursor.fetchall()
for i, row in enumerate(fields):
    if i < 15:  # Show first 15 fields
        print(f"  {row[0]:30} {row[1]}")

db.connection.close()
