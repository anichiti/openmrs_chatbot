#!/usr/bin/env python3
"""
Connect to OpenMRS MySQL via Docker Container
Since MySQL port is not exposed to Windows, we connect through Docker
"""

import subprocess
import json
import sys
from utils.logger import setup_logger

logger = setup_logger(__name__)

def run_docker_mysql_query(query):
    """Execute MySQL query inside the Docker container"""
    container = "openmrs-chatbot-dev"
    
    # Escape quotes for shell
    query = query.replace('"', '\\"')
    
    cmd = f'docker exec {container} mysql -uopenmrs -popenmrs chatbot-dev -e "{query}"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.error(f"Docker MySQL error: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        logger.error(f"Error running Docker MySQL command: {str(e)}")
        return None

def test_docker_connection():
    """Test connection to MySQL via Docker"""
    print("\n" + "=" * 70)
    print("OpenMRS Database Connection Test (via Docker)")
    print("=" * 70)
    print(f"\n📦 Using Docker Container: openmrs-chatbot-dev")
    print(f"   Database: chatbot-dev")
    print(f"   User: openmrs")
    print(f"   Method: Docker exec (port 3308 exposed to host)\n")
    
    print("🔄 Attempting to connect...\n")
    
    queries = [
        ("Total Patients", "SELECT COUNT(*) as count FROM patient WHERE voided = false;"),
        ("Total Encounters", "SELECT COUNT(*) as count FROM encounter WHERE voided = false;"),
        ("Total Observations", "SELECT COUNT(*) as count FROM obs WHERE voided = false;"),
        ("Sample Patient", """
            SELECT p.patient_id, pn.given_name, pn.family_name, per.gender, per.birthdate
            FROM patient p
            JOIN person_name pn ON p.patient_id = pn.person_id
            JOIN person per ON p.patient_id = per.person_id
            WHERE p.voided = false AND pn.voided = false
            LIMIT 1;
        """),
    ]
    
    success = False
    print("📊 Database Statistics:\n")
    
    for test_name, query in queries:
        try:
            result = run_docker_mysql_query(query)
            if result:
                print(f"   ✓ {test_name}:")
                for line in result.strip().split('\n')[:3]:  # Show first 3 lines
                    print(f"      {line}")
                success = True
            else:
                print(f"   ✗ {test_name}: Query failed")
        except Exception as e:
            print(f"   ✗ {test_name}: {str(e)}")
    
    if success:
        print("\n" + "=" * 70)
        print("✅ Successfully connected to OpenMRS via Docker!")
        print("=" * 70)
        print("\nTo use this connection method in your chatbot, set:")
        print("   USE_DOCKER_CONNECTION=true")
        print("   in .env file\n")
    else:
        print("\n" + "=" * 70)
        print("❌ Connection failed")
        print("=" * 70 + "\n")
    
    return success

if __name__ == "__main__":
    success = test_docker_connection()
    sys.exit(0 if success else 1)
