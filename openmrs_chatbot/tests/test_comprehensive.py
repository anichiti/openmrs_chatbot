#!/usr/bin/env python3
"""
Comprehensive chatbot readiness test
Tests all components before running the full chatbot
"""
import sys
import time
import json
from pathlib import Path

def test_imports():
    """Test all required imports"""
    print("\n" + "="*60)
    print("TESTING IMPORTS")
    print("="*60)
    
    try:
        print("  ✓ ollama")
        import ollama
        print("  ✓ chromadb")
        import chromadb
        print("  ✓ mysql.connector")
        import mysql.connector
        print("  ✓ dotenv")
        from dotenv import load_dotenv
        print("\n✓ All imports successful")
        return True
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        return False

def test_ollama_connection():
    """Test connection to Ollama service"""
    print("\n" + "="*60)
    print("TESTING OLLAMA CONNECTION")
    print("="*60)
    
    try:
        import ollama
        from utils.config import OLLAMA_HOST, OLLAMA_MODEL
        
        print(f"  Host: {OLLAMA_HOST}")
        print(f"  Model: {OLLAMA_MODEL}")
        
        client = ollama.Client(host=OLLAMA_HOST)
        print("  ✓ Ollama client created")
        
        # Try to list models
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt="Hello",
            stream=False,
        )
        
        if response and response.get('response'):
            print(f"  ✓ Model {OLLAMA_MODEL} responded")
            print(f"    Response length: {len(response['response'])} chars")
            return True
        else:
            print(f"  ✗ Model {OLLAMA_MODEL} did not respond properly")
            return False
            
    except Exception as e:
        print(f"  ✗ Ollama test failed: {e}")
        return False

def test_database_connection():
    """Test connection to OpenMRS database"""
    print("\n" + "="*60)
    print("TESTING DATABASE CONNECTION")
    print("="*60)
    
    try:
        from database.db import OpenMRSDatabase
        from utils.config import DB_HOST, DB_PORT, DB_NAME
        
        print(f"  Host: {DB_HOST}:{DB_PORT}")
        print(f"  Database: {DB_NAME}")
        
        db = OpenMRSDatabase()
        if db.connect():
            print("  ✓ Database connected")
            
            # Quick test query
            result = db.execute_query("SELECT COUNT(*) as count FROM patient WHERE voided = false")
            db.disconnect()
            
            if result.get('data'):
                count = result['data'][0].get('count', 0)
                print(f"  ✓ Database active: {count} patients found")
                return True
            else:
                print("  ✗ Database query failed")
                return False
        else:
            print("  ✗ Database connection failed")
            return False
            
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        return False

def test_knowledge_base():
    """Test knowledge base initialization"""
    print("\n" + "="*60)
    print("TESTING KNOWLEDGE BASE")
    print("="*60)
    
    try:
        from vectorstore.chroma import VectorStore
        
        vs = VectorStore()
        print("  ✓ VectorStore created")
        
        vs.initialize_collections()
        print("  ✓ Collections initialized")
        
        return True
    except Exception as e:
        print(f"  ✗ Knowledge base test failed: {e}")
        return False

def test_agents():
    """Test agent initialization"""
    print("\n" + "="*60)
    print("TESTING AGENTS")
    print("="*60)
    
    try:
        from agents.triage_agent import TriageAgent
        from agents.sql_agent import SQLAgent
        from agents.mcp_agent import MCPAgent
        from agents.knowledge_agent import KnowledgeAgent
        from agents.response_agent import ResponseAgent
        
        print("  Creating TriageAgent...", end=" ")
        ta = TriageAgent()
        print("✓")
        
        print("  Creating SQLAgent...", end=" ")
        sa = SQLAgent()
        print("✓")
        
        print("  Creating MCPAgent...", end=" ")
        mcp = MCPAgent()
        print("✓")
        
        print("  Creating KnowledgeAgent...", end=" ")
        ka = KnowledgeAgent()
        print("✓")
        
        print("  Creating ResponseAgent...", end=" ")
        ra = ResponseAgent()
        print("✓")
        
        print("\n  ✓ All agents created successfully")
        return True
    except Exception as e:
        print(f"\n  ✗ Agent test failed: {e}")
        return False

def test_patient_query():
    """Test a complete patient query flow"""
    print("\n" + "="*60)
    print("TESTING PATIENT QUERY FLOW")
    print("="*60)
    
    try:
        from main import ClinicalChatbot
        
        print("  Initializing chatbot...", end=" ")
        chatbot = ClinicalChatbot()
        print("✓")
        
        # Test a simple query
        print("  Processing test query...", end=" ")
        result = chatbot.process_query("What are recent observations for patient 24")
        print("✓")
        
        # Check result structure
        required_keys = ['user_type', 'intent', 'response', 'sources']
        missing = [k for k in required_keys if k not in result]
        
        if missing:
            print(f"  ✗ Result missing keys: {missing}")
            return False
        
        print(f"\n  Result Summary:")
        print(f"    - User Type: {result['user_type']}")
        print(f"    - Intent: {result['intent']}")
        print(f"    - Sources: {', '.join(result['sources'])}")
        print(f"    - Response preview: {result['response'][:100]}...")
        
        return True
    except Exception as e:
        print(f"\n  ✗ Query flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CLINICAL CHATBOT - COMPREHENSIVE TEST")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Ollama Connection", test_ollama_connection),
        ("Database Connection", test_database_connection),
        ("Knowledge Base", test_knowledge_base),
        ("Agents", test_agents),
        ("Patient Query Flow", test_patient_query),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\nFATAL ERROR in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED! Chatbot is ready to use.")
        print("\nRun: python main.py")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check log above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
