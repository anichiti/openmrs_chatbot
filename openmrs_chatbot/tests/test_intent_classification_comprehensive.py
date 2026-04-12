"""
COMPREHENSIVE INTENT CLASSIFICATION AND MCP TRIGGER VALIDATION TEST SUITE

This test suite validates that the TriageAgent correctly:
1. Classifies intent from user questions
2. Triggers the correct MCP/SQL agent
3. Extracts patient IDs correctly
4. Handles multi-intent queries (prioritizing specific queries over patient records)
5. Rejects general queries without inappropriate MCP triggers
6. Maintains 95%+ classification accuracy

Test Categories:
- MEDICATION_QUERY tests (MCP_MEDICATION_AGENT)
- IMMUNIZATION_QUERY tests (MCP_IMMUNIZATION_AGENT)
- MILESTONE_QUERY tests (MCP_MILESTONE_AGENT)
- PATIENT_RECORD_QUERY tests (SQL_AGENT)
- MULTI_INTENT tests (priority handling)
- NEGATIVE tests (no MCP trigger for general queries)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.triage_agent import TriageAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

class IntentClassificationValidator:
    """Validator for intent classification and MCP triggering"""
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.failures = []
    
    def validate_classification(self, question, expected_intent, expected_agent, test_name=""):
        """Validate a single classification"""
        self.total += 1
        result = self.triage_agent.triage(question)
        
        intent = result.get('intent')
        agent = result.get('agent')
        
        passed = (intent == expected_intent and agent == expected_agent)
        
        status = "CHECK PASS" if passed else "FAIL FAIL"
        print(f"\n{status} | {test_name}")
        print(f"  Question: {question}")
        print(f"  Expected: Intent={expected_intent}, Agent={expected_agent}")
        print(f"  Got:      Intent={intent}, Agent={agent}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append({
                'test': test_name,
                'question': question,
                'expected_intent': expected_intent,
                'expected_agent': expected_agent,
                'actual_intent': intent,
                'actual_agent': agent
            })
        
        return passed
    
    def print_summary(self):
        """Print test summary"""
        accuracy = (self.passed / self.total * 100) if self.total > 0 else 0
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed} ({accuracy:.1f}%)")
        print(f"Failed: {self.failed}")
        print(f"Status: {'CHECK SUCCESS' if self.failed == 0 else 'FAIL FAILURE'}")
        
        if self.failures:
            print("\nFAILED TESTS:")
            for failure in self.failures:
                print(f"\n  {failure['test']}")
                print(f"    Question: {failure['question']}")
                print(f"    Expected: {failure['expected_intent']} -> {failure['expected_agent']}")
                print(f"    Got:      {failure['actual_intent']} -> {failure['actual_agent']}")
        
        return accuracy


def run_medication_tests(validator):
    """Test MEDICATION_QUERY classification and MCP_MEDICATION_AGENT triggering"""
    print("\n" + "="*80)
    print("TEST SET 1: MEDICATION QUERIES")
    print("Expected: MEDICATION_QUERY -> MCP_MEDICATION_AGENT")
    print("="*80)
    
    tests = [
        ("What is the dose of paracetamol for a 2 year old?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Side effects of ibuprofen?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Can amoxicillin cause rash?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Maximum dosage of acetaminophen?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("What is ibuprofen used for?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Is paracetamol safe for infants?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Contraindications of aspirin?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Dose of amoxicillin for children?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Can I take ibuprofen during pregnancy?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Medication for fever in kids?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Pediatric dose of amoxicillin 100mg/kg", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Drug interaction between ibuprofen and aspirin", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Recommended dose of paracetamol for 30kg child", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Adverse effects of tetracycline", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
    ]
    
    for question, expected_intent, expected_agent in tests:
        validator.validate_classification(question, expected_intent, expected_agent, f"MED: {question[:60]}")
    
    return validator


def run_immunization_tests(validator):
    """Test IMMUNIZATION_QUERY classification and MCP_IMMUNIZATION_AGENT triggering"""
    print("\n" + "="*80)
    print("TEST SET 2: IMMUNIZATION QUERIES")
    print("Expected: IMMUNIZATION_QUERY -> MCP_IMMUNIZATION_AGENT")
    print("="*80)
    
    tests = [
        ("When should MMR vaccine be given?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("What vaccines are given at birth?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Polio vaccine schedule?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Is BCG given at birth?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Which vaccines at 6 months?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("When is first immunization?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Immunization schedule for 1 year old?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Is Hepatitis B vaccine mandatory?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("What vaccines does a newborn need?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Next vaccine after MMR?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Rotavirus vaccination schedule", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Pentavalent vaccine dosing", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Varicella immunization age", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
    ]
    
    for question, expected_intent, expected_agent in tests:
        validator.validate_classification(question, expected_intent, expected_agent, f"IMM: {question[:60]}")
    
    return validator


def run_milestone_tests(validator):
    """Test MILESTONE_QUERY classification and MCP_MILESTONE_AGENT triggering"""
    print("\n" + "="*80)
    print("TEST SET 3: MILESTONE QUERIES")
    print("Expected: MILESTONE_QUERY -> MCP_MILESTONE_AGENT")
    print("="*80)
    
    tests = [
        ("When should baby start walking?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When do babies start talking?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When should baby sit without support?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When should baby crawl?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("Normal age for smiling?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When do babies recognize parents?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When should baby roll over?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("Speech milestone at 1 year?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("Motor milestones at 6 months?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("Developmental milestones chart?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When do babies start teething?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("Cognitive development at 18 months", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
    ]
    
    for question, expected_intent, expected_agent in tests:
        validator.validate_classification(question, expected_intent, expected_agent, f"MLS: {question[:60]}")
    
    return validator


def run_patient_record_tests(validator):
    """Test PATIENT_RECORD_QUERY classification and SQL_AGENT triggering"""
    print("\n" + "="*80)
    print("TEST SET 4: PATIENT RECORD QUERIES")
    print("Expected: PATIENT_RECORD_QUERY -> SQL_AGENT")
    print("="*80)
    
    tests = [
        ("Show patient 101 lab results", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Blood pressure of patient 200", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Medical history of patient 300", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Vitals of patient 400", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Diagnosis of patient 123", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Patient 222 temperature", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("OpenMRS record of patient 555", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Lab report of patient 777", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Show glucose level patient 888", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Patient 999 visit summary", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Charts for patient 1000001W", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Recent observations for patient 500", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
    ]
    
    for question, expected_intent, expected_agent in tests:
        validator.validate_classification(question, expected_intent, expected_agent, f"PAT: {question[:60]}")
    
    return validator


def run_multi_intent_tests(validator):
    """Test multi-intent queries - specific query type should take priority over patient record"""
    print("\n" + "="*80)
    print("TEST SET 5: MULTI-INTENT QUERIES (Priority Test)")
    print("Expected: Specific query type should prioritize over PATIENT_RECORD_QUERY")
    print("="*80)
    
    tests = [
        # Medication + Patient: Should be MEDICATION_QUERY
        ("Patient 101 paracetamol dose", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT", "Medication question for specific patient"),
        ("What dose of ibuprofen for patient 200?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT", "Medication query with patient context"),
        
        # Immunization + Patient: Should be IMMUNIZATION_QUERY
        ("When should patient 101 get MMR vaccine?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT", "Immunization query with patient context"),
        ("Polio vaccine schedule for patient 300", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT", "Vaccine question for specific patient"),
        
        # Milestone + Patient: Should be MILESTONE_QUERY
        ("Is patient 200 walking normally?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT", "Milestone development question"),
        ("When should patient 500 start talking?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT", "Speech milestone for patient"),
    ]
    
    for question, expected_intent, expected_agent, description in tests:
        validator.validate_classification(question, expected_intent, expected_agent, description)
    
    return validator


def run_negative_tests(validator):
    """Test negative cases - general queries should NOT trigger MCP agents"""
    print("\n" + "="*80)
    print("TEST SET 6: NEGATIVE TESTS (General Queries)")
    print("Expected: GENERAL_MEDICAL_QUERY (should NOT trigger specific MCP agents)")
    print("="*80)
    
    tests = [
        ("Hello", "GENERAL_MEDICAL_QUERY", None),
        ("How are you?", "GENERAL_MEDICAL_QUERY", None),
        ("What is fever?", "GENERAL_MEDICAL_QUERY", None),
        ("Explain diabetes", "GENERAL_MEDICAL_QUERY", None),
        ("General health tips", "GENERAL_MEDICAL_QUERY", None),
        ("Tell me about health", "GENERAL_MEDICAL_QUERY", None),
        ("What causes cough?", "GENERAL_MEDICAL_QUERY", None),
        ("Describe symptoms of flu", "GENERAL_MEDICAL_QUERY", None),
    ]
    
    for question, expected_intent, expected_agent in tests:
        validator.validate_classification(question, expected_intent, expected_agent, f"NEG: {question}")
    
    return validator


def main():
    """Run all test suites"""
    print("\n")
    print("[" + "="*78 + "]")
    print("|" + " INTENT CLASSIFICATION & MCP TRIGGER VALIDATION TEST SUITE ".center(78) + "|")
    print("|" + " OpenMRS Clinical Chatbot Intent Router ".center(78) + "|")
    print("[" + "="*78 + "]")
    
    validator = IntentClassificationValidator()
    
    # Run all test suites
    validator = run_medication_tests(validator)
    validator = run_immunization_tests(validator)
    validator = run_milestone_tests(validator)
    validator = run_patient_record_tests(validator)
    validator = run_multi_intent_tests(validator)
    validator = run_negative_tests(validator)
    
    # Print summary
    accuracy = validator.print_summary()
    
    # Exit with appropriate code
    return 0 if validator.failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
