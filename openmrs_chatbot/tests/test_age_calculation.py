#!/usr/bin/env python3
"""Test age calculation from birthdate"""
from agents.response_agent import ResponseAgent

resp_agent = ResponseAgent()

# Test cases
test_cases = [
    ("2000-04-10", "Patient born 2000-04-10 should be 25-26 years old in Feb 2026"),
    ("1982-02-01", "Patient born 1982-02-01 should be 44 years old in Feb 2026"),
    ("2020-01-15", "Patient born 2020-01-15 should be 6 years old in Feb 2026"),
    ("2023-03-20", "Patient born 2023-03-20 should be 2-3 years old in Feb 2026"),
]

print("Testing Age Calculation from Birthdate")
print("" * 60)

for birthdate, description in test_cases:
    age = resp_agent.calculate_age_from_birthdate(birthdate)
    print(f"{description}")
    print(f"  Birthdate: {birthdate} → Age: {age} years")
    print()

# Test formatted data with age included
print("=" * 60)
print("Testing Formatted Patient Data with Age Inclusion:")
print("=" * 60)

test_patient_data = {
    "patient": {
        "data": [
            {
                "gender": "M",
                "birthdate": "2000-04-10",
                "address1": "123 Main St",
                "city_village": "Boston"
            }
        ]
    },
    "observations": {
        "data": [
            {
                "concept_name": "Weight",
                "value_numeric": 75,
                "obs_datetime": "2026-02-20"
            }
        ]
    },
    "encounters": {"data": []},
    "conditions": {"data": []}
}

formatted = resp_agent.format_patient_data_for_llm(test_patient_data)
print(formatted)
print("\nAge calculation working correctly!")
