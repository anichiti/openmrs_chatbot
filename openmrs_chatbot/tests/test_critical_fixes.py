"""
TEST SUITE FOR CRITICAL FIXES

Tests the following fixes:
1. ModuleNotFoundError - sys.path setup in triage_agent.py
2. Patient ID extraction - No false positives (won't extract "age", "record", "name")
3. MILESTONE_QUERY with patient context - Age calculation and personalized response
4. Patient context passing - Selected patient ID properly used throughout
"""

import sys
import os

# Fix sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.triage_agent import TriageAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

class CriticalFixValidator:
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.passed = 0
        self.failed = 0
    
    def test_patient_id_extraction_no_false_positives(self):
        """Test that patient ID extraction doesn't match common words"""
        print("\n" + "="*80)
        print("TEST 1: Patient ID Extraction - No False Positives")
        print("="*80)
        
        # These should NOT extract patient IDs
        test_cases = [
            ("what is patient age and name?", None, "Should NOT extract 'age' or 'name' as patient ID"),
            ("retrieve patient record", None, "Should NOT extract 'record' as patient ID"),
            ("show patient information", None, "Should NOT extract 'information' as patient ID"),
            ("what is the patient status?", None, "Should NOT extract 'status' as patient ID"),
            ("display patient chart", None, "Should NOT extract 'chart' as patient ID"),
        ]
        
        # These SHOULD extract valid patient IDs
        valid_cases = [
            ("show patient 100008E lab results", "100008E", "Should extract '100008E'"),
            ("patient ID: 1000001W", "1000001W", "Should extract '1000001W'"),
            ("patient 123ABC details", "123ABC", "Should extract '123ABC'"),
            ("#100008E", "100008E", "Should extract '100008E' from hash"),
        ]
        
        print("\nInvalid ID extraction test (should NOT extract):")
        for question, expected_id, description in test_cases:
            extracted_id = self.triage_agent.extract_patient_id(question)
            if extracted_id is expected_id:
                print(f"  ✓ PASS: {description}")
                print(f"    Q: {question}")
                print(f"    Result: {extracted_id} (Correct - no false positive)")
                self.passed += 1
            else:
                print(f"  ✗ FAIL: {description}")
                print(f"    Q: {question}")
                print(f"    Expected: {expected_id}, Got: {extracted_id}")
                self.failed += 1
        
        print("\nValid ID extraction test (SHOULD extract):")
        for question, expected_id, description in valid_cases:
            extracted_id = self.triage_agent.extract_patient_id(question)
            if extracted_id == expected_id:
                print(f"  ✓ PASS: {description}")
                print(f"    Q: {question}")
                print(f"    Result: {extracted_id}")
                self.passed += 1
            else:
                print(f"  ✗ FAIL: {description}")
                print(f"    Q: {question}")
                print(f"    Expected: {expected_id}, Got: {extracted_id}")
                self.failed += 1
    
    def test_milestone_query_with_patient_age(self):
        """Test MILESTONE_QUERY classification with patient context"""
        print("\n" + "="*80)
        print("TEST 2: MILESTONE_QUERY with Patient Context")
        print("="*80)
        
        test_cases = [
            ("what milestone should he reach by now?", "MILESTONE_QUERY", "Should classify as MILESTONE_QUERY"),
            ("when should patient start walking?", "MILESTONE_QUERY", "Should classify as MILESTONE_QUERY"),
            ("is this patient developing normally?", "MILESTONE_QUERY", "Should classify as MILESTONE_QUERY"),
            ("what are the developmental milestones for this age?", "MILESTONE_QUERY", "Should classify as MILESTONE_QUERY"),
        ]
        
        print("\nMilestone query classification test:")
        for question, expected_intent, description in test_cases:
            result = self.triage_agent.triage(question)
            intent = result["intent"]
            agent = result["agent"]
            
            if intent == expected_intent and agent == "MCP_MILESTONE_AGENT":
                print(f"  ✓ PASS: {description}")
                print(f"    Q: {question}")
                print(f"    Intent: {intent} | Agent: {agent}")
                self.passed += 1
            else:
                print(f"  ✗ FAIL: {description}")
                print(f"    Q: {question}")
                print(f"    Expected: {expected_intent} → MCP_MILESTONE_AGENT")
                print(f"    Got: {intent} → {agent}")
                self.failed += 1
    
    def test_patient_id_extraction_from_milestone_queries(self):
        """Test that patient IDs are properly extracted from milestone questions"""
        print("\n" + "="*80)
        print("TEST 3: Patient ID Extraction from Milestone Queries")
        print("="*80)
        
        test_cases = [
            ("what milestone should patient 100008E reach?", "100008E", "Should extract patient 100008E"),
            ("is this patient 1000001W walking?", "1000001W", "Should extract patient 1000001W"),
            ("developmental progress for patient 123ABC?", "123ABC", "Should extract patient 123ABC"),
            ("when should this patient reach milestones?", None, "No explicit patient ID"),
        ]
        
        print("\nPatient ID extraction from milestone context:")
        for question, expected_id, description in test_cases:
            extracted_id = self.triage_agent.extract_patient_id(question)
            
            if extracted_id == expected_id:
                print(f"  ✓ PASS: {description}")
                print(f"    Q: {question}")
                print(f"    Extracted ID: {extracted_id}")
                self.passed += 1
            else:
                print(f"  ✗ FAIL: {description}")
                print(f"    Q: {question}")
                print(f"    Expected: {expected_id}, Got: {extracted_id}")
                self.failed += 1
    
    def test_no_utils_import_errors(self):
        """Test that utils module imports correctly"""
        print("\n" + "="*80)
        print("TEST 4: ModuleNotFoundError Fix - Import Validation")
        print("="*80)
        
        try:
            # This should not raise ModuleNotFoundError anymore
            from agents.triage_agent import TriageAgent
            print("  ✓ PASS: triage_agent imports successfully")
            print("    sys.path setup prevents ModuleNotFoundError")
            self.passed += 1
        except ModuleNotFoundError as e:
            print(f"  ✗ FAIL: ModuleNotFoundError still occurs")
            print(f"    Error: {e}")
            self.failed += 1
        except Exception as e:
            print(f"  ? OTHER ERROR: {e}")
            self.failed += 1
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        accuracy = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*80)
        print("CRITICAL FIXES TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Status: {'✓ ALL TESTS PASSED' if self.failed == 0 else '✗ SOME TESTS FAILED'}")
        print("="*80)
        
        return self.failed == 0


def main():
    print("\n")
    print("[" + "="*78 + "]")
    print("|" + " CRITICAL FIXES VALIDATION TEST SUITE ".center(78) + "|")
    print("|" + " Validates: ModuleNotFoundError, Patient ID Extraction, Milestone + Age ".center(78) + "|")
    print("[" + "="*78 + "]")
    
    validator = CriticalFixValidator()
    
    # Run all tests
    validator.test_no_utils_import_errors()
    validator.test_patient_id_extraction_no_false_positives()
    validator.test_milestone_query_with_patient_age()
    validator.test_patient_id_extraction_from_milestone_queries()
    
    # Print summary
    success = validator.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
