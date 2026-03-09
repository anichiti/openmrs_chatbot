#!/usr/bin/env python3
"""
Test Database Connection to OpenMRS
Run this to verify your database credentials work
"""

import mysql.connector
from mysql.connector import Error
from utils.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import setup_logger

logger = setup_logger(__name__)


def test_connection():
    """Test database connection and display sample data"""
    print("\n" + "=" * 70)
    print("OpenMRS Database Connection Test")
    print("=" * 70)
    print(f"\n📍 Connection Details:")
    print(f"   Host: {DB_HOST}")
    print(f"   Port: {DB_PORT}")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print(f"   Password: {'*' * len(DB_PASSWORD)}")
    print(f"\n🔄 Attempting to connect...\n")

    try:
        from database.db import OpenMRSDatabase
        db = OpenMRSDatabase()
        if not db.connect():
            print("❌ CONNECTION FAILED: Could not connect to OpenMRS database\n")
            return False
        print("✅ SUCCESS! Connected to OpenMRS database\n")
        connection = db.connection
        cursor = connection.cursor(dictionary=True)
        
        # Test queries
        tests = [
            ("Total Patients", "SELECT COUNT(*) as count FROM patient WHERE voided = false"),
            ("Total Encounters", "SELECT COUNT(*) as count FROM encounter WHERE voided = false"),
            ("Total Observations", "SELECT COUNT(*) as count FROM obs WHERE voided = false"),
            ("Sample Patient", """
                SELECT p.patient_id, pn.given_name, pn.family_name, per.gender, per.birthdate
                FROM patient p
                JOIN person_name pn ON p.patient_id = pn.person_id
                JOIN person per ON p.patient_id = per.person_id
                WHERE p.voided = false AND pn.voided = false
                LIMIT 1
            """),
        ]
        
        print("📊 Database Statistics:\n")
        for test_name, query in tests:
            try:
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    print(f"   ✓ {test_name}: {result}")
                else:
                    print(f"   ✗ {test_name}: No data")
            except Error as e:
                print(f"   ✗ {test_name}: {str(e)}")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 70)
        print("✅ You're ready to use the chatbot with live OpenMRS data!")
        print("=" * 70 + "\n")
        
        return True
        
    except Error as e:
        print(f"❌ CONNECTION FAILED: {str(e)}\n")
        print("Troubleshooting steps:")
        print("1. Verify OpenMRS is running on localhost:8080")
        print("2. Check database credentials in .env file")
        print("3. Try alternative credentials:")
        print("   - DB_USER=admin, DB_PASSWORD=admin123")
        print("   - DB_USER=openmrs, DB_PASSWORD=openmrs")
        print("4. Check if MySQL port (3306) is accessible")
        print("\nTo find correct credentials:")
        print("   1. Go to OpenMRS Admin: http://localhost:8080/openmrs/admin")
        print("   2. Look for Settings or System Settings")
        print("   3. Find database connection info")
        print("   4. Or check: WEB-INF/runtime.properties file\n")
        
        return False


if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
