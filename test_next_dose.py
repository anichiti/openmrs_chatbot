#!/usr/bin/env python3
"""Test next scheduled dose and missed vaccines"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openmrs_chatbot'))

from agents.immunization_openmrs_fetcher import ImmunizationOpenMRSFetcher

print("=" * 80)
print("IMMUNIZATION FEATURES - NEXT DOSE & MISSED VACCINES TEST")
print("=" * 80)

fetcher = ImmunizationOpenMRSFetcher()
patient_id = "100008E"

# Test next scheduled dose
print("\n1. NEXT SCHEDULED DOSE")
print("-" * 80)
next_dose = fetcher.get_next_scheduled_dose(patient_id)
if next_dose:
    print(f"✓ Next dose: {next_dose['vaccine_name']}")
    print(f"  Scheduled for: {next_dose['next_dose_date']}")
    print(f"  Recorded: {next_dose['recorded_date']}")
else:
    print("✗ No next scheduled dose found")

# Test missed vaccines
print("\n2. MISSED/OVERDUE VACCINES")
print("-" * 80)
missed = fetcher.get_missed_vaccines(patient_id)
if missed:
    print(f"✓ Found {len(missed)} overdue vaccines:")
    for v in missed:
        print(f"  - {v['name']}")
else:
    print("✗ No missed vaccines or patient is up to date")

# Test immunization history with actual dates
print("\n3. IMMUNIZATION HISTORY WITH ACTUAL DATES")
print("-" * 80)
history = fetcher.get_immunization_history(patient_id)
print(f"Found {len(history)} immunization records:")
for h in history:
    print(f"\nVaccine: {h['vaccine_name']}")
    print(f"  Given: {h['date_given']}")
    print(f"  Next dose: {h.get('next_dose_date', 'Not scheduled')}")
    print(f"  Dose #: {h.get('dose_number', 'Unknown')}")

print("\n" + "=" * 80)
fetcher.disconnect()
print("Test complete")
