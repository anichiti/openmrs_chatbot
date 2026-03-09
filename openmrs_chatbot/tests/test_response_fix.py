#!/usr/bin/env python3
"""Quick test of response fix"""
import subprocess
import sys

# Prepare input: select doctor role, patient 21, ask age, then exit
test_input = "1\n21\nwhat is the patient age?\nexit\n"

try:
    result = subprocess.run(
        [sys.executable, "main.py"],
        input=test_input,
        text=True,
        capture_output=False,
        cwd="."
    )
except Exception as e:
    print(f"Error: {e}")
