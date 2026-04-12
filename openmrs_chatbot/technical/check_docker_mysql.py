#!/usr/bin/env python3
"""
Check Docker MySQL Port Exposure
Finds the MySQL container and shows how to connect from Windows
"""

import subprocess
import json
import sys

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1

def find_mysql_container():
    """Find MySQL container and its port mapping"""
    print("\n" + "=" * 70)
    print("Docker MySQL Container Information")
    print("=" * 70 + "\n")
    
    # Check if Docker is running
    output, code = run_command("docker ps")
    if code != 0:
        print("❌ Docker is not running or not installed")
        print("Please ensure Docker is running\n")
        return False
    
    # List containers
    print("📦 Running Containers:\n")
    print(output)
    
    # Look for MySQL container
    print("\n🔍 Looking for MySQL container...\n")
    output, code = run_command("docker ps --filter 'ancestor=mysql' --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'")
    
    if output:
        print("Found MySQL containers:")
        print(output)
        return True
    else:
        print("❌ No MySQL container found")
        print("Trying to find any database container...\n")
        
        output, code = run_command("docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}\t{{.Image}}'")
        if output:
            print(output)
        
        return False

if __name__ == "__main__":
    find_mysql_container()
    
    print("\n" + "=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("""
1. Look for MySQL port mapping in the output above
   Example: 0.0.0.0:3306->3306/tcp means port 3306 is exposed
   
2. If port 3306 is exposed, the connection should work
   
3. If port is NOT exposed, try:
   docker port <container_id> 3306
   to see the mapped port
   
4. If still not working, you may need to:
   - Run queries inside the container
   - Or expose the port in docker-compose.yml
   
5. To run queries via Docker:
   python test_db_connection_docker.py
""")
