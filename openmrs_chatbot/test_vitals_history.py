#!/usr/bin/env python3
"""Test vitals history retrieval"""

from database.db import OpenMRSDatabase
import json

db = OpenMRSDatabase()
vitals = db.get_patient_vitals_history(100008, limit=10)

print(f'Type of vitals: {type(vitals)}')
print(f'Vitals object: {vitals}')

if isinstance(vitals, dict):
    print(f'\nDict keys: {vitals.keys()}')
    for key, value in vitals.items():
        print(f'  {key}: {value}')
