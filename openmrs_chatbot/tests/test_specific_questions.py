#!/usr/bin/env python
"""Test specific question filtering in response formatting"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.response_agent import ResponseAgent
from agents.sql_agent import SQLAgent

def test_specific_question_filtering():
    """Test that responses filter correctly based on the question asked"""
    
    # Initialize database and response agent
    sql_agent = SQLAgent()
    response_agent = ResponseAgent()
    
    # Get a patient's data
    patient_data = sql_agent.query_patient_record(7)
    
    if not patient_data:
        print("ERROR: Could not fetch patient data")
        return False
    
    print("\n" + "="*80)
    print("TESTING SPECIFIC QUESTION FILTERING")
    print("="*80)
    
    all_tests_passed = True
    
    # Test 1: Name Question
    print("\nTEST 1: 'What is patient 7 name?'")
    print("-" * 60)
    question1 = "What is patient 7 name?"
    response1 = response_agent.format_patient_data_for_llm(patient_data, question=question1)
    print(response1)
    
    has_name = "Name:" in response1
    has_vitals = "VITAL SIGNS" in response1.upper()
    has_observations = "OBSERVATIONS" in response1.upper()
    has_encounters = "ENCOUNTERS" in response1.upper()
    has_conditions = "CONDITIONS" in response1.upper()
    
    test1_pass = has_name and not has_vitals and not has_observations and not has_encounters and not has_conditions
    
    print(f"\n  Has Name: {has_name} {'[OK]' if has_name else '[FAIL]'}")
    print(f"  Has Vitals: {has_vitals} {'[FAIL - SHOULD NOT]' if has_vitals else '[OK]'}")
    print(f"  Has Observations: {has_observations} {'[FAIL - SHOULD NOT]' if has_observations else '[OK]'}")
    print(f"  Has Encounters: {has_encounters} {'[FAIL - SHOULD NOT]' if has_encounters else '[OK]'}")
    print(f"  Has Conditions: {has_conditions} {'[FAIL - SHOULD NOT]' if has_conditions else '[OK]'}")
    print(f"  RESULT: {'PASS' if test1_pass else 'FAIL'}")
    
    if not test1_pass:
        all_tests_passed = False
    
    # Test 2: Age Question
    print("\nTEST 2: 'What is patient 7 age?'")
    print("-" * 60)
    question2 = "What is patient 7 age?"
    response2 = response_agent.format_patient_data_for_llm(patient_data, question=question2)
    print(response2)
    
    has_age = "Age:" in response2
    has_vitals = "VITAL SIGNS" in response2.upper()
    has_observations = "OBSERVATIONS" in response2.upper()
    
    test2_pass = has_age and not has_vitals and not has_observations
    
    print(f"\n  Has Age: {has_age} {'[OK]' if has_age else '[FAIL]'}")
    print(f"  Has Vitals: {has_vitals} {'[FAIL - SHOULD NOT]' if has_vitals else '[OK]'}")
    print(f"  Has Observations: {has_observations} {'[FAIL - SHOULD NOT]' if has_observations else '[OK]'}")
    print(f"  RESULT: {'PASS' if test2_pass else 'FAIL'}")
    
    if not test2_pass:
        all_tests_passed = False
    
    # Test 3: Weight and Height
    print("\nTEST 3: 'What is patient 7 weight and height?'")
    print("-" * 60)
    question3 = "What is patient 7 weight and height?"
    response3 = response_agent.format_patient_data_for_llm(patient_data, question=question3)
    print(response3)
    
    has_weight = "Weight" in response3
    has_height = "Height" in response3
    # When asking for vitals specifically, VITAL SIGNS section is ok
    # But other vitals like temperature and BP should NOT be there
    has_temp = "Temperature" in response3
    has_bp = "Blood Pressure" in response3
    
    test3_pass = has_weight and has_height and not has_temp and not has_bp
    
    print(f"\n  Has Weight: {has_weight} {'[OK]' if has_weight else '[FAIL]'}")
    print(f"  Has Height: {has_height} {'[OK]' if has_height else '[FAIL]'}")
    print(f"  Has Temperature: {has_temp} {'[FAIL - SHOULD NOT]' if has_temp else '[OK]'}")
    print(f"  Has BP: {has_bp} {'[FAIL - SHOULD NOT]' if has_bp else '[OK]'}")
    print(f"  RESULT: {'PASS' if test3_pass else 'FAIL'}")
    
    if not test3_pass:
        all_tests_passed = False
    
    # Test 4: Conditions (with English filtering)
    print("\nTEST 4: 'What conditions does patient 7 have?'")
    print("-" * 60)
    question4 = "What conditions does patient 7 have?"
    response4 = response_agent.format_patient_data_for_llm(patient_data, question=question4)
    print(response4)
    
    has_conditions = "CONDITIONS" in response4.upper()
    has_vitals = "VITAL SIGNS" in response4.upper()
    
    # Check for non-English words
    non_english_indicators = ["Cylindre", "Maladies", "Tuberculose", "urinaire", "hyalin", "infectieuses", "peritoine"]
    has_non_english = any(indicator in response4 for indicator in non_english_indicators)
    
    test4_pass = has_conditions and not has_vitals and not has_non_english
    
    print(f"\n  Has Conditions: {has_conditions} {'[OK]' if has_conditions else '[FAIL]'}")
    print(f"  Has Vitals: {has_vitals} {'[FAIL - SHOULD NOT]' if has_vitals else '[OK]'}")
    print(f"  Has Non-English: {has_non_english} {'[FAIL - SHOULD NOT - NO FRENCH/SPANISH]' if has_non_english else '[OK - ENGLISH ONLY]'}")
    print(f"  RESULT: {'PASS' if test4_pass else 'FAIL'}")
    
    if not test4_pass:
        all_tests_passed = False
    
    # Summary
    print("\n" + "="*80)
    print(f"OVERALL RESULT: {'ALL TESTS PASSED' if all_tests_passed else 'SOME TESTS FAILED'}")
    print("="*80)
    
    return all_tests_passed

if __name__ == '__main__':
    try:
        success = test_specific_question_filtering()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
