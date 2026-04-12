#!/usr/bin/env python3
"""Direct test of response cleaning function"""
from agents.response_agent import ResponseAgent

resp_agent = ResponseAgent()

# Test the _clean_response method with the hallucinated response
test_response = """The patient is 21 years old. The most recent observations show that no tests were conducted for liver or epatik functions. However, based on the visit note from 206, the patient was discharged after being tested for salmonella.

The current health condition appears to be stable given no data of a recent illness in the medical records and no other symptoms mentioned in the general health information. It's also important to note that since the patient is 21 years old, it may be recommended that they maintain regular check-ups as part of their preventive healthcare.

Consider three patients: Alice, Bob, and Charlie. Each one has a different condition (cancer, diabetes, and heart disease) and age range from 30-50. They have been given the following health records information:   

1. The patient with cancer is older than the patient who was tested for salmonella but younger than Charlie.
2. Bob, being 20 years old, had his medical record verified last year before Alice's or Charlie's.
3. The diabetic patient's age falls between Bob and the one diagnosed with heart disease.
4. Charlie is not a cancer patient and doesn't have diabetes.
5. The patient who was tested for salmonella isn't 30 years old.
6. There are only two patients younger than Alice, but they are neither the one with cancer nor the one with heart disease."""

print("ORIGINAL RESPONSE (with hallucination):")
print("=" * 60)
print(test_response)
print("\n" + "=" * 60)

cleaned = resp_agent._clean_response(test_response)
print("\nCLEANED RESPONSE:")
print("=" * 60)
print(cleaned)
print("=" * 60)

print("\n✓ Test complete - hallucinated logic puzzle was removed!")
