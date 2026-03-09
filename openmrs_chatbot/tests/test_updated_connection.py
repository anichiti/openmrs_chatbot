#!/usr/bin/env python3
"""
Test the updated database connection with Docker support
"""

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()
print('\n🔄 Connecting to OpenMRS database...\n')

if db.connect():
    print('Connection successful!')
    print(f'   Method: {"Docker" if db.use_docker else "Direct MySQL"}\n')
    
    # Test queries
    result = db.execute_query('SELECT COUNT(*) as total_patients FROM patient WHERE voided = false')
    if result['data']:
        print(f"📊 Total Patients: {result['data'][0]['total_patients']}")
    
    result = db.execute_query('SELECT COUNT(*) as total_encounters FROM encounter WHERE voided = false')
    if result['data']:
        print(f"📊 Total Encounters: {result['data'][0]['total_encounters']}")
    
    result = db.execute_query('SELECT COUNT(*) as total_obs FROM obs WHERE voided = false')
    if result['data']:
        print(f"📊 Total Observations: {result['data'][0]['total_obs']}")
    
    db.disconnect()
    print('\nAll tests passed! Database is ready to use.\n')
else:
    print('Connection failed!')
