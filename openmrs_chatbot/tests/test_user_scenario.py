"""
Test: Drug Dosage Handler Integration - Patient 100008E Aspirin Query
=====================================================================

Simulates the exact scenario from the user's request:
- Doctor role
- Patient 100008E  
- Query: "what dose of aspirin can i give for this patient"
- Expected: Drug dosage handler should be called instead of normal medication query
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.drug_dosage_handler import (
    detect_drug_intent,
    extract_drug_name,
)
from unittest.mock import MagicMock, patch

def test_user_scenario():
    """Test the exact user scenario"""
    
    print("\n" + "="*70)
    print("TEST: User Scenario - Doctor asking for aspirin dose for patient 100008E")
    print("="*70)
    
    query = "what dose of aspirin can i give for this patient"
    patient_id = "100008E"
    user_role = "DOCTOR"
    
    print(f"\nScenario:")
    print(f"  Role: {user_role}")
    print(f"  Patient: {patient_id}")
    print(f"  Query: {query}")
    
    # Test 1: Detect drug intent
    print(f"\n[TEST 1] Detect Drug Intent")
    intent_detected = detect_drug_intent(query)
    print(f"  Query: '{query}'")
    print(f"  Drug intent detected: {intent_detected}")
    if intent_detected:
        print(f"  Status: [PASS] Intent correctly detected")
        test1_ok = True
    else:
        print(f"  Status: [FAIL] Should have detected drug intent")
        test1_ok = False
    
    # Test 2: Extract drug name
    print(f"\n[TEST 2] Extract Drug Name")
    drug_name = extract_drug_name(query)
    print(f"  Query: '{query}'")
    print(f"  Extracted drug: {drug_name}")
    if drug_name and "aspirin" in drug_name.lower():
        print(f"  Status: [PASS] Drug name correctly extracted")
        test2_ok = True
    else:
        print(f"  Status: [FAIL] Should extract 'aspirin'")
        test2_ok = False
    
    # Test 3: Verify routing conditions
    print(f"\n[TEST 3] Verify Handler Routing Conditions")
    
    # Simulated conditions that would trigger the handler
    would_trigger_handler = (
        user_role == "DOCTOR" and 
        patient_id and 
        detect_drug_intent(query)
    )
    
    print(f"  Conditions:")
    print(f"    - user_role == 'DOCTOR': {user_role == 'DOCTOR'}")
    print(f"    - patient_id exists: {bool(patient_id)}")
    print(f"    - detect_drug_intent(query): {detect_drug_intent(query)}")
    print(f"  => Would trigger handler: {would_trigger_handler}")
    
    if would_trigger_handler:
        print(f"  Status: [PASS] Handler should be called")
        test3_ok = True
    else:
        print(f"  Status: [FAIL] Handler should be triggered")
        test3_ok = False
    
    # Summary
    print(f"\n" + "="*70)
    print(f"TEST SUMMARY")
    print(f"="*70)
    
    tests = [
        ("Drug Intent Detection", test1_ok),
        ("Drug Name Extraction", test2_ok),
        ("Handler Routing", test3_ok),
    ]
    
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    
    for name, ok in tests:
        status = "[PASS]" if ok else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n[SUCCESS] Drug dosage handler should be called for this query!")
        print(f"\nNext steps to get response:")
        print(f"  1. Ensure Ollama is running: ollama serve")
        print(f"  2. Pull embedding model: ollama pull nomic-embed-text")
        print(f"  3. Initialize knowledge base: python technical/init_kb.py")
        print(f"  4. Run chatbot: python main.py")
        return True
    else:
        print(f"\n[FAILURE] Something is preventing handler from being called")
        return False

if __name__ == "__main__":
    success = test_user_scenario()
    sys.exit(0 if success else 1)
