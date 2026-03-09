from database.db import OpenMRSDatabase

db = OpenMRSDatabase()
if db.connect():
    result = db.execute_query('DESCRIBE patient')
    if result['error'] is None:
        print("Patient table columns:")
        for row in result['data']:
            print(f"  {row['Field']}: {row['Type']}")
    else:
        print(f"Error: {result['error']}")
    
    # Also check person_name table
    result2 = db.execute_query('DESCRIBE person_name')
    if result2['error'] is None:
        print("\nPerson_name table columns:")
        for row in result2['data']:
            print(f"  {row['Field']}: {row['Type']}")
    else:
        print(f"Error: {result2['error']}")
    
    db.disconnect()
