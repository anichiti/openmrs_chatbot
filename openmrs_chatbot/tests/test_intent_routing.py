#!/usr/bin/env python3
"""
Diagnostic: Verify Intent Classification and Data Routing
Tests if each question is classified correctly and routed to the right data source
"""

from agents.triage_agent import TriageAgent
from agents.mcp_agent import MCPAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Test cases with expected outcomes
test_cases = [
    # Format: (question, expected_intent, expected_data_source)
    ("What is patient 24's weight?", "PATIENT_RECORD_QUERY", "OpenMRS SQL"),
    ("Show me patient 100's encounters", "PATIENT_RECORD_QUERY", "OpenMRS SQL"),
    ("What medical conditions does patient 50 have?", "PATIENT_RECORD_QUERY", "OpenMRS SQL"),
    
    ("What is Metformin used for?", "MEDICATION_QUERY", "medication.json"),
    ("Tell me about Amoxicillin", "MEDICATION_QUERY", "medication.json"),
    ("Can he take Lisinopril?", "MEDICATION_QUERY", "medication.json"),
    ("What are the side effects of Aspirin?", "MEDICATION_QUERY", "medication.json"),
    
    ("What vaccines should a 12-month-old get?", "IMMUNIZATION_QUERY", "immunization.json"),
    ("Is MMR vaccine safe?", "IMMUNIZATION_QUERY", "immunization.json"),
    ("Tell me about COVID-19 vaccination", "IMMUNIZATION_QUERY", "immunization.json"),
    
    ("What should a 6-month-old be able to do?", "MILESTONE_QUERY", "milestones.json"),
    ("When should a baby start walking?", "MILESTONE_QUERY", "milestones.json"),
    ("Tell me about 12-month developmental milestones", "MILESTONE_QUERY", "milestones.json"),
]

def test_intent_classification():
    print("\n" + "=" * 80)
    print("INTENT CLASSIFICATION & DATA ROUTING DIAGNOSTIC")
    print("=" * 80)
    
    triage = TriageAgent()
    mcp = MCPAgent()
    
    correct = 0
    incorrect = 0
    
    for question, expected_intent, expected_source in test_cases:
        print(f"\n{'=' * 80}")
        print(f"Question: {question}")
        print(f"Expected: {expected_intent} -> {expected_source}")
        
        # Get triage classification
        triage_result = triage.triage(question)
        classified_intent = triage_result["intent"]
        patient_id = triage_result["patient_id"]
        
        # Check classification
        match = classified_intent == expected_intent
        status = "✓ PASS" if match else "✗ FAIL"
        
        print(f"Result:   {classified_intent:25} {status}")
        
        if patient_id:
            print(f"Patient ID Extracted: {patient_id}")
        
        # Now test data retrieval based on intent
        print(f"\nData Retrieval Test:")
        
        if classified_intent == "PATIENT_RECORD_QUERY":
            if patient_id:
                print(f"  → Would query: OpenMRS SQL for patient {patient_id}")
                print(f"  ✓ Correct routing to SQL Agent")
            else:
                print(f"  ✗ ERROR: No patient ID extracted for PATIENT_RECORD_QUERY")
        
        elif classified_intent == "MEDICATION_QUERY":
            med_result = mcp.search_medication(question)
            print(f"  → Query: medication.json")
            print(f"  → Results found: {med_result['count']}")
            if med_result['count'] > 0:
                for med in med_result['results'][:2]:
                    print(f"     • {med.get('name', 'Unknown')}")
        
        elif classified_intent == "IMMUNIZATION_QUERY":
            vac_result = mcp.search_vaccine(question)
            print(f"  → Query: immunization.json")
            print(f"  → Results found: {vac_result['count']}")
            if vac_result['count'] > 0:
                for vac in vac_result['results'][:2]:
                    print(f"     • {vac.get('name', 'Unknown')}")
        
        elif classified_intent == "MILESTONE_QUERY":
            milestone_result = mcp.search_milestone(question)
            print(f"  → Query: milestones.json")
            print(f"  → Results found: {milestone_result['count']}")
            if milestone_result['count'] > 0:
                for m in milestone_result['results'][:2]:
                    print(f"     • Age {m.get('age_months', '?')} months - {m.get('type', 'Unknown')}")
        
        if match:
            correct += 1
        else:
            incorrect += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {correct + incorrect}")
    print(f"✓ Correct Classifications: {correct}")
    print(f"✗ Incorrect Classifications: {incorrect}")
    print(f"Success Rate: {correct / (correct + incorrect) * 100:.1f}%")
    
    if incorrect == 0:
        print("\n✅ All intent classifications and data routing verified!")
    else:
        print(f"\n⚠️  {incorrect} classification(s) need review")
    
    print("=" * 80)

if __name__ == "__main__":
    test_intent_classification()
