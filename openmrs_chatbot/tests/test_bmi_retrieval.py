#!/usr/bin/env python
"""Test BMI retrieval and calculation"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.sql_agent import SQLAgent
from agents.response_agent import ResponseAgent

sql_agent = SQLAgent()
response_agent = ResponseAgent()

print("\n" + "="*80)
print("BMI TEST - Retrieving and Calculating BMI")
print("="*80)

# Get patient 7 data
patient_data = sql_agent.query_patient_record(7)

if patient_data:
    print("\n1. Testing BMI from database retrieval:")
    print("-" * 60)
    vitals = patient_data.get("vitals", {}).get("data", [])
    
    has_bmi = False
    height_cm = None
    weight_kg = None
    bmi_value = None
    
    for vital in vitals:
        vital_name = (vital.get('vital_name', '') or '').lower()
        if 'bmi' in vital_name:
            has_bmi = True
            bmi_value = vital.get('value_numeric')
            print(f"[OK] BMI found in database: {vital.get('vital_name')} = {bmi_value}")
        elif 'height' in vital_name:
            height_cm = vital.get('value_numeric')
            print(f"  Height: {vital.get('vital_name')} = {height_cm}")
        elif 'weight' in vital_name:
            weight_kg = vital.get('value_numeric')
            print(f"  Weight: {vital.get('vital_name')} = {weight_kg}")
    
    if not has_bmi:
        print("[INFO] BMI not found in database, will calculate from height and weight")
    
    print("\n2. Testing BMI Calculation:")
    print("-" * 60)
    if height_cm and weight_kg:
        calc_bmi = response_agent.calculate_bmi(weight_kg, height_cm)
        print(f"Height: {height_cm} cm, Weight: {weight_kg} kg")
        print(f"Calculated BMI: {calc_bmi} kg/m2")
    
    print("\n3. Testing BMI in formatted response:")
    print("-" * 60)
    
    # Test 1: BMI query
    question = "What is patient 7 BMI?"
    response = response_agent.format_patient_data_for_llm(patient_data, question=question)
    print(f"Question: '{question}'")
    print(f"Response:\n{response}")
    
    has_bmi_in_response = "bmi" in response.lower()
    print(f"\n[OK] BMI in response: {has_bmi_in_response}")
    
    # Test 2: Vitals query (should include BMI with other vitals)
    print("\n" + "-" * 60)
    question = "What are patient 7 vitals?"
    response = response_agent.format_patient_data_for_llm(patient_data, question=question)
    print(f"Question: '{question}'")
    print(f"Response:\n{response}")
    
    has_bmi_in_response = "bmi" in response.lower()
    print(f"\n[OK] BMI in vitals response: {has_bmi_in_response}")
    
    print("\n" + "="*80)
    print("BMI TEST COMPLETE")
    print("="*80)
else:
    print("ERROR: Could not fetch patient data")
