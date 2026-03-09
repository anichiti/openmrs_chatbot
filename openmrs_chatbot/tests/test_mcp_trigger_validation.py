"""
MCP TRIGGER VALIDATION TEST

Validates that:
1. Correct MCP agent is triggered for each intent
2. No wrong MCP agent is triggered
3. SQL agent is correctly triggered for patient records
4. Multi-intent queries route to correct MCP (not SQL)

Critical Rules to Validate:
- Medication -> MCP_MEDICATION_AGENT ONLY (not SQL_AGENT)
- Immunization -> MCP_IMMUNIZATION_AGENT ONLY (not SQL_AGENT)
- Milestone -> MCP_MILESTONE_AGENT ONLY (not SQL_AGENT)
- Patient Data -> SQL_AGENT ONLY (not MCP)
- Multi-intent: Specific query type > Patient record type
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.triage_agent import TriageAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MCPTriggerValidator:
    """Validator specifically for MCP agent triggering"""
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.tests_passed = 0
        self.tests_failed = 0
        self.critical_failures = []
    
    def validate_mcp_trigger(self, question, expected_agent, test_category=""):
        """Validate that the correct MCP agent is triggered"""
        result = self.triage_agent.triage(question)
        actual_agent = result.get('agent')
        
        passed = actual_agent == expected_agent
        status = "CHECK" if passed else "FAIL CRITICAL FAILURE"
        
        print(f"\n{status} | {test_category}")
        print(f"  Q: {question}")
        print(f"  Expected Agent: {expected_agent}")
        print(f"  Actual Agent:   {actual_agent}")
        
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
            self.critical_failures.append({
                'question': question,
                'expected': expected_agent,
                'actual': actual_agent,
                'category': test_category
            })
        
        return passed
    
    def validate_no_mcp_misfire(self, question, forbidden_agent, test_name=""):
        """Validate that a specific MCP agent is NOT triggered (misfire check)"""
        result = self.triage_agent.triage(question)
        actual_agent = result.get('agent')
        
        passed = actual_agent != forbidden_agent
        status = "CHECK" if passed else "FAIL MISFIRE"
        
        print(f"\n{status} | {test_name}")
        print(f"  Q: {question}")
        print(f"  Forbidden: {forbidden_agent}")
        print(f"  Got:       {actual_agent}")
        print(f"  Status: {'OK' if passed else 'WRONG MCP TRIGGERED!'}")
        
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
            self.critical_failures.append({
                'type': 'MISFIRE',
                'question': question,
                'forbidden_agent': forbidden_agent,
                'actual_agent': actual_agent,
                'test_name': test_name
            })
        
        return passed
    
    def print_summary(self):
        """Print validation summary"""
        total = self.tests_passed + self.tests_failed
        accuracy = (self.tests_passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*80)
        print("MCP TRIGGER VALIDATION SUMMARY")
        print("="*80)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Status: {'CHECK ALL MCP TRIGGERS CORRECT' if self.tests_failed == 0 else 'FAIL CRITICAL MCP TRIGGER FAILURES'}")
        
        if self.critical_failures:
            print("\n" + "="*80)
            print("CRITICAL FAILURES (MCP TRIGGER ERRORS)")
            print("="*80)
            for i, failure in enumerate(self.critical_failures, 1):
                if failure.get('type') == 'MISFIRE':
                    print(f"\nMISFIRE #{i}: {failure.get('test_name')}")
                    print(f"  Q: {failure['question']}")
                    print(f"  Should NOT trigger: {failure['forbidden_agent']}")
                    print(f"  Actually triggered: {failure['actual_agent']}")
                else:
                    print(f"\nFAILURE #{i}: {failure.get('category')}")
                    print(f"  Q: {failure['question']}")
                    print(f"  Expected: {failure['expected']}")
                    print(f"  Got:      {failure['actual']}")


def test_medication_mcp_triggering(validator):
    """Test that MEDICATION_QUERY always triggers MCP_MEDICATION_AGENT"""
    print("\n" + "="*80)
    print("TEST: MEDICATION_QUERY -> MCP_MEDICATION_AGENT")
    print("="*80)
    
    questions = [
        "What is the dose of paracetamol for a 2 year old?",
        "Side effects of ibuprofen?",
        "Prescribe amoxicillin dosage",
        "How much aspirin is safe?",
        "Medication for fever in children?",
        "Pediatric dose calculation for 15kg child",
    ]
    
    for q in questions:
        validator.validate_mcp_trigger(q, 'MCP_MEDICATION_AGENT', 'MEDICATION->MCP')
    
    return validator


def test_immunization_mcp_triggering(validator):
    """Test that IMMUNIZATION_QUERY always triggers MCP_IMMUNIZATION_AGENT"""
    print("\n" + "="*80)
    print("TEST: IMMUNIZATION_QUERY -> MCP_IMMUNIZATION_AGENT")
    print("="*80)
    
    questions = [
        "When should MMR vaccine be given?",
        "Polio vaccination schedule?",
        "Is BCG given at birth?",
        "Which vaccines at 6 months?",
        "Hepatitis B vaccine dose?",
        "Immunization schedule for newborns?",
    ]
    
    for q in questions:
        validator.validate_mcp_trigger(q, 'MCP_IMMUNIZATION_AGENT', 'IMMUNIZATION->MCP')
    
    return validator


def test_milestone_mcp_triggering(validator):
    """Test that MILESTONE_QUERY always triggers MCP_MILESTONE_AGENT"""
    print("\n" + "="*80)
    print("TEST: MILESTONE_QUERY -> MCP_MILESTONE_AGENT")
    print("="*80)
    
    questions = [
        "When should baby start walking?",
        "When do babies start talking?",
        "When should baby sit without support?",
        "Motor milestones at 6 months?",
        "Speech development at 18 months?",
        "When do babies smile?",
    ]
    
    for q in questions:
        validator.validate_mcp_trigger(q, 'MCP_MILESTONE_AGENT', 'MILESTONE->MCP')
    
    return validator


def test_patient_record_sql_triggering(validator):
    """Test that PATIENT_RECORD_QUERY always triggers SQL_AGENT"""
    print("\n" + "="*80)
    print("TEST: PATIENT_RECORD_QUERY -> SQL_AGENT")
    print("="*80)
    
    questions = [
        "Show patient 101 lab results",
        "Blood pressure of patient 200",
        "Medical history of patient 300",
        "Patient 555 vitals",
        "Diagnosis of patient 999",
        "Temperature for patient 777",
    ]
    
    for q in questions:
        validator.validate_mcp_trigger(q, 'SQL_AGENT', 'PATIENT->SQL')
    
    return validator


def test_mcp_misfire_prevention(validator):
    """Test that wrong MCPs are NOT triggered (misfire prevention)"""
    print("\n" + "="*80)
    print("TEST: MCP MISFIRE PREVENTION")
    print("Ensure medication questions DON'T trigger SQL_AGENT")
    print("="*80)
    
    # Medication questions must NOT trigger SQL_AGENT
    med_questions = [
        "What is the dose of paracetamol for a 2 year old?",
        "Side effects of ibuprofen?",
        "Contraindications of aspirin?",
    ]
    
    for q in med_questions:
        validator.validate_no_mcp_misfire(q, 'SQL_AGENT', f'MED_NO_SQL: {q[:50]}')
    
    # Immunization questions must NOT trigger SQL_AGENT
    print("\n" + "-"*80)
    print("Ensure immunization questions DON'T trigger SQL_AGENT")
    print("-"*80)
    
    imm_questions = [
        "When should MMR vaccine be given?",
        "Polio vaccination schedule?",
        "BCG vaccine timing?",
    ]
    
    for q in imm_questions:
        validator.validate_no_mcp_misfire(q, 'SQL_AGENT', f'IMM_NO_SQL: {q[:50]}')
    
    # Milestone questions must NOT trigger SQL_AGENT
    print("\n" + "-"*80)
    print("Ensure milestone questions DON'T trigger SQL_AGENT")
    print("-"*80)
    
    milestone_questions = [
        "When should baby start walking?",
        "Speech development timeline?",
        "Motor milestones at 6 months?",
    ]
    
    for q in milestone_questions:
        validator.validate_no_mcp_misfire(q, 'SQL_AGENT', f'MLS_NO_SQL: {q[:50]}')
    
    return validator


def test_multi_intent_priority(validator):
    """Test that multi-intent queries prioritize specific query type over patient record"""
    print("\n" + "="*80)
    print("TEST: MULTI-INTENT QUERY PRIORITY")
    print("Medication + Patient -> Should be MCP_MEDICATION_AGENT (NOT SQL_AGENT)")
    print("="*80)
    
    # These have BOTH patient IDs and medication keywords
    # Should prioritize MEDICATION_QUERY over PATIENT_RECORD_QUERY
    questions = [
        ("Patient 101 paracetamol dose", 'MCP_MEDICATION_AGENT'),
        ("What dose of ibuprofen for patient 200?", 'MCP_MEDICATION_AGENT'),
        ("Show patient 300 aspirin dosage", 'MCP_MEDICATION_AGENT'),
    ]
    
    for q, expected_agent in questions:
        validator.validate_mcp_trigger(q, expected_agent, f'MULTI_PRIORITY: {q[:50]}')
        # Also verify SQL_AGENT is NOT triggered
        validator.validate_no_mcp_misfire(q, 'SQL_AGENT', f'MULTI_NO_SQL: {q[:50]}')
    
    return validator


def main():
    """Run all MCP trigger validation tests"""
    print("\n")
    print("[" + "="*78 + "]")
    print("|" + " MCP TRIGGER VALIDATION TEST SUITE ".center(78) + "|")
    print("|" + " Critical Agent Routing Verification ".center(78) + "|")
    print("[" + "="*78 + "]")
    
    validator = MCPTriggerValidator()
    
    # Run all validation tests
    validator = test_medication_mcp_triggering(validator)
    validator = test_immunization_mcp_triggering(validator)
    validator = test_milestone_mcp_triggering(validator)
    validator = test_patient_record_sql_triggering(validator)
    validator = test_mcp_misfire_prevention(validator)
    validator = test_multi_intent_priority(validator)
    
    # Print summary
    validator.print_summary()
    
    return 0 if validator.tests_failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
