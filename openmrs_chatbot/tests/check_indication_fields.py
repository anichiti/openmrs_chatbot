#!/usr/bin/env python3
"""Check what indication/reason fields are available in OpenMRS past medications"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from database.db import OpenMRSDatabase

db = OpenMRSDatabase()
db.connect()
cursor = db.connection.cursor(dictionary=True)

# Get a sample past medication with all its data
cursor.execute('''
SELECT o.ORDER_ID, o.ORDER_REASON, o.ORDER_REASON_NON_CODED, o.INSTRUCTIONS,
       o.AUTO_EXPIRE_DATE, o.DATE_ACTIVATED, o.DATE_STOPPED,
       do.DRUG_INVENTORY_ID, d.NAME as DRUG_NAME, do.DOSE, do.DOSING_INSTRUCTIONS,
       o.VOIDED
FROM orders o
JOIN drug_order do ON o.ORDER_ID = do.ORDER_ID
JOIN drug d ON do.DRUG_INVENTORY_ID = d.DRUG_ID
WHERE o.VOIDED = 0
AND (
    (o.AUTO_EXPIRE_DATE IS NOT NULL AND o.AUTO_EXPIRE_DATE <= NOW())
    OR (o.DATE_STOPPED IS NOT NULL AND o.DATE_STOPPED <= NOW())
)
LIMIT 1
''')

result = cursor.fetchone()
if result:
    print("Sample past medication data:")
    for key, val in result.items():
        print(f"  {key}: {val}")
else:
    print("No past medications found")
    # Let's check if there are ANY past medications at all
    cursor.execute('SELECT COUNT(*) as cnt FROM orders WHERE VOIDED = 0')
    print(f"Total non-voided orders: {cursor.fetchone()['cnt']}")

db.disconnect()
