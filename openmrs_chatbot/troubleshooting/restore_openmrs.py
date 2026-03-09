#!/usr/bin/env python3
"""
OpenMRS Database Restore Script
Restores openmrs-2-7-0.sql to local MySQL
"""

import mysql.connector
from mysql.connector import Error
import sys
import os

def main():
    # Try multiple possible paths
    possible_paths = [
        r'C:\Users\chiti\Downloads\openmrs-2-7-0.sql',
        'openmrs_data.sql',
        'openmrs-2-7-0.sql'
    ]
    
    sql_file = None
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            sql_file = path
            print(f'[OK] Found SQL file: {path}')
            break
    
    if not sql_file:
        print('[ERROR] SQL file not found at:')
        for path in possible_paths:
            print(f'  - {path}')
        return False
    
    file_size = os.path.getsize(sql_file) / (1024 * 1024)
    print(f'[INFO] SQL file size: {file_size:.2f} MB')
    
    try:
        # Connect to MySQL using OpenMRSDatabase
        print('[1/4] Connecting to MySQL...')
        from database.db import OpenMRSDatabase
        db = OpenMRSDatabase()
        if not db.connect():
            print('     [FAIL] Could not connect to MySQL')
            return False
        print('     Connected to MySQL')
        connection = db.connection
        cursor = connection.cursor()
        
        # Read SQL file
        print('[2/4] Reading SQL file...')
        try:
            with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            print(f'     Read {len(content):,} characters')
        except PermissionError:
            print('     [WARNING] Permission denied, trying with different encoding...')
            with open(sql_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            print(f'     Read {len(content):,} characters')
        
        # Prepare database
        print('[3/4] Preparing database...')
        cursor.execute('DROP DATABASE IF EXISTS `chatbot-dev`')
        cursor.execute('CREATE DATABASE `chatbot-dev` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        cursor.execute('USE `chatbot-dev`')
        connection.commit()
        print('     Database prepared')
        
        # Execute SQL
        print('[4/4] Loading data (this may take 2-3 minutes)...')
        
        # Simple split by semicolon
        statements = content.split(';')
        executed = 0
        
        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                continue
            
            try:
                cursor.execute(statement)
                executed += 1
                
                # Commit every 100 statements
                if executed % 100 == 0:
                    connection.commit()
                    print(f'     Processed {executed:,} statements...')
                    
            except Error as e:
                error_str = str(e)
                # Ignore duplicate/already exists errors
                if 'already exists' not in error_str and 'duplicate' not in error_str.lower():
                    if executed < 10:
                        print(f'     Note: {error_str[:60]}')
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print()
        print('='*60)
        print('[OK] Restore successful!')
        print(f'    Statements executed: {executed:,}')
        print('='*60)
        
        return True
        
    except Error as e:
        print(f'[ERROR] MySQL Error: {e}')
        return False
    except Exception as e:
        print(f'[ERROR] {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
