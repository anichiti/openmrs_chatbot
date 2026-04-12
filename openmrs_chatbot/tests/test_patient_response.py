#!/usr/bin/env python
"""Quick test to verify patient data usage in responses"""
import sys
from agents.response_agent import ResponseAgent
from agents.sql_agent import SQLAgent
from agents.triage_agent import TriageAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

def test_with_patient_data():
    """Test response generation with actual patient data"""
    print("\n" + "="*70)
    print("Testing Patient Data Usage in Responses")
    print("="*70 + "\n")
    
    # Initialize agents
    triageagent = TriageAgent()
    sql_agent = SQLAgent()
    response_agent = ResponseAgent()
    
    # Test with patient ID 24
    patient_id = "24"
    
    print(f"[1] Querying patient {patient_id} from database...")
    patient_data = sql_agent.query_patient_record(patient_id)
    
    # Show what we retrieved
    print("\n[2] Patient data retrieved:")
    for key, value in patient_data.items():
        if isinstance(value, dict) and 'data' in value:
            count = len(value.get('data', []))
            error = value.get('error')
            print(f"   - {key}: {count} records" + (f" (error: {error})" if error else ""))
    
    # Test doctor query
    doctor_question = "Can I prescribe metformin to her?"
    print(f"\n[3] Testing DOCTOR query: '{doctor_question}'")
    
    triag_result = triageagent.triage(doctor_question)
    print(f"   Triage result: {triag_result}")
    
    context_data = {
        "sources": ["Patient Record (OpenMRS)"],
        "kb_content": "Metformin is an oral antidiabetic drug",
        "patient_data": patient_data
    }
    
    response = response_agent.generate_doctor_response(doctor_question, context_data)
    print("\n   Response:")
    print(f"   {response}\n")
    
    # Test patient query
    patient_question = "what is her weight?"
    print(f"[4] Testing PATIENT query: '{patient_question}'")
    
    context_data = {
        "sources": ["Patient Record (OpenMRS)"],
        "kb_content": "Weight is typically measured in kilograms or pounds",
        "patient_data": patient_data
    }
    
    response = response_agent.generate_patient_response(patient_question, context_data)
    print("\n   Response:")
    print(f"   {response}\n")
    
    print("="*70)
    print("Test complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_with_patient_data()
