#!/usr/bin/env python3
"""Test response cleaning for calculation attempts"""
from agents.response_agent import ResponseAgent

resp_agent = ResponseAgent()

# Simulate the bad response with calculation
bad_response = """Based on the patient's demographics and available data, we can accurately determine the age of the patient using a simple calculation. The patient's birth date is provided as 2000-04-10. To calculate their current age, subtract their birth year (2000) from the current year (2021). This will give us 21 years - 2000 = 2021 - 2000 = 21 years. Therefore, the patient is 21 years old."""

print("Testing Response Cleaning for Calculation Attempts")
print("=" * 70)
print("\nORIGINAL (Bad - has calculation reasoning):")
print(bad_response)

cleaned = resp_agent._clean_response(bad_response)
print("\n" + "=" * 70)
print("CLEANED (Current Age: 25 years from data should be used):")
print(cleaned)
print("=" * 70)

if "To calculate" in cleaned or "subtract" in cleaned or "therefore" in cleaned.lower():
    print("\n✗ FAIL: Calculation attempt still in cleaned response")
else:
    print("\nPASS: Calculation attempt was removed from response")
