#!/usr/bin/env python3
"""Final verification of immunization fixes"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from agents.immunization_openmrs_fetcher import ImmunizationOpenMRSFetcher

print("=" * 80)
print("IMMUNIZATION FEATURE - FINAL VERIFICATION")
print("=" * 80)

fetcher = ImmunizationOpenMRSFetcher()

# Test patient
patient_id = "100008E"

print("\n✓ ISSUE 1: Vaccine names now showing actual vaccine names")
print("-" * 80)
history = fetcher.get_immunization_history(patient_id)
print(f"Found {len(history)} immunization records:")
for i, vac in enumerate(history, 1):
    print(f"{i}. {vac['vaccine_name']} - Given on {vac['date_given']}")

if history and history[0]['vaccine_name'] != 'Immunizations':
    print("✓ PASS: Vaccine names are specific, not generic 'Immunizations'")
else:
    print("✗ FAIL: Vaccine names still generic")

print("\n✓ ISSUE 2: DTaP now appears in recommendations")
print("-" * 80)
recommendations = fetcher.get_recommended_vaccines(patient_id)
vaccine_names = [v['name'] for v in recommendations]
print(f"Found {len(recommendations)} recommended vaccines:")
for i, vac in enumerate(vaccine_names, 1):
    print(f"{i}. {vac}")

if any('DTaP' in v for v in vaccine_names):
    print("✓ PASS: DTaP is now in the recommendations")
else:
    print("✗ FAIL: DTaP is not in recommendations")

if any('DPT' in v for v in vaccine_names):
    print("✓ PASS: DPT is also in the recommendations")
else:
    print("✗ FAIL: DPT is not in recommendations")

print("\n✓ ISSUE 3: All scheduled vaccines appearing")
print("-" * 80)
expected_vaccines = ['MMR', 'COVID-19', 'DPT', 'Polio', 'Influenza', 'DTaP']
for expected in expected_vaccines:
    found = any(expected in v for v in vaccine_names)
    status = "✓" if found else "✗"
    print(f"{status} {expected}: {'Found' if found else 'NOT FOUND'}")

total_vaccines = len(recommendations)
print(f"\nTotal recommended vaccines: {total_vaccines}")
if total_vaccines >= 6:
    print("✓ PASS: At least 6 vaccines recommended")
else:
    print("✗ FAIL: Not all expected vaccines are being recommended")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

fetcher.disconnect()
