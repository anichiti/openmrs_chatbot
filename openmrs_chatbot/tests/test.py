#!/usr/bin/env python3

"""
Comprehensive test suite for OpenMRS Clinical Chatbot
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.triage_agent import TriageAgent
from agents.mcp_agent import MCPAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)


def test_triage_agent():
    print("\n" + "=" * 60)
    print("Testing Triage Agent")
    print("=" * 60)
    
    triage = TriageAgent()
    
    test_cases = [
        {
            "question": "Patient 123 presents with persistent cough and elevated WBC count, what are differential diagnoses?",
            "expected_type": "DOCTOR",
            "expected_intent": "PATIENT_RECORD_QUERY"
        },
        {
            "question": "My child has a fever, what should I do?",
            "expected_type": "PATIENT",
            "expected_intent": "SYMPTOM_QUERY"
        },
        {
            "question": "What is the contraindication for Amoxicillin?",
            "expected_type": "DOCTOR",
            "expected_intent": "MEDICATION_QUERY"
        },
        {
            "question": "When should my baby get the MMR vaccine?",
            "expected_type": "PATIENT",
            "expected_intent": "IMMUNIZATION_QUERY"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['question'][:50]}...")
        result = triage.triage(test['question'])
        
        print(f"  User Type: {result['user_type']} (expected: {test['expected_type']})")
        print(f"  Intent: {result['intent']} (expected: {test['expected_intent']})")
        
        if result['patient_id']:
            print(f"  Patient ID: {result['patient_id']}")


def test_mcp_agent():
    print("\n" + "=" * 60)
    print("Testing MCP Agent")
    print("=" * 60)
    
    mcp = MCPAgent()
    
    print("\n1. Testing Medication Query:")
    med_result = mcp.query_medication_db(drug_name="Amoxicillin")
    print(f"   Found {med_result['count']} medications")
    if med_result['results']:
        print(f"   - {med_result['results'][0]['name']}")
        print(f"     Indications: {', '.join(med_result['results'][0]['indications'][:2])}")
    
    print("\n2. Testing Medication Search:")
    search_result = mcp.search_medication("diabetes")
    print(f"   Found {search_result['count']} results for 'diabetes'")
    if search_result['results']:
        for med in search_result['results'][:2]:
            print(f"   - {med['name']}")
    
    print("\n3. Testing Immunization Query:")
    vac_result = mcp.query_immunization_db(vaccine_name="MMR")
    print(f"   Found {vac_result['count']} vaccines")
    if vac_result['results']:
        print(f"   - {vac_result['results'][0]['name']}")
        print(f"     Recommended ages: {', '.join(vac_result['results'][0]['recommended_age_groups'])}")
    
    print("\n4. Testing Milestone Query:")
    milestone_result = mcp.get_milestone_by_age(6)
    print(f"   Found {milestone_result['count']} milestone sets for 6 months")
    if milestone_result['results']:
        for m in milestone_result['results'][:2]:
            print(f"   - {m['type']}: {m['milestones'][0]}")


def test_json_databases():
    print("\n" + "=" * 60)
    print("Testing JSON Databases Integrity")
    print("=" * 60)
    
    databases = {
        "Medication": "data/medication.json",
        "Immunization": "data/immunization.json",
        "Milestone": "data/milestones.json"
    }
    
    for db_name, db_path in databases.items():
        print(f"\nChecking {db_name} database ({db_path})...")
        
        if not os.path.exists(db_path):
            print(f"   ✗ File not found: {db_path}")
            continue
        
        try:
            with open(db_path, 'r') as f:
                data = json.load(f)
            
            if db_name == "Medication":
                count = len(data.get("medications", []))
                print(f"   ✓ Database loaded: {count} medications")
            elif db_name == "Immunization":
                count = len(data.get("vaccines", []))
                print(f"   ✓ Database loaded: {count} vaccines")
            else:  # Milestone
                count = len(data.get("milestones", []))
                print(f"   ✓ Database loaded: {count} milestone entries")
                
        except json.JSONDecodeError:
            print(f"   ✗ Invalid JSON format")
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")


def test_configuration():
    print("\n" + "=" * 60)
    print("Testing Configuration")
    print("=" * 60)
    
    try:
        from utils import config
        
        print(f"\n✓ Configuration loaded successfully")
        print(f"  Database: {config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        print(f"  Log Level: {config.LOG_LEVEL}")
        print(f"  Vectorstore: {config.VECTORSTORE_DIR}")
        
        if not config.OPENAI_API_KEY or config.OPENAI_API_KEY == "":
            print(f"  ⚠ Warning: OPENAI_API_KEY not set in environment")
        else:
            print(f"  ✓ OpenAI API Key configured")
            
    except Exception as e:
        print(f"\n✗ Configuration error: {str(e)}")


def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " OpenMRS Clinical Chatbot - Test Suite ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    
    test_configuration()
    test_json_databases()
    test_triage_agent()
    test_mcp_agent()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nTo run the chatbot:")
    print("  python main.py")
    print("\nTo initialize knowledge base:")
    print("  python init_kb.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
