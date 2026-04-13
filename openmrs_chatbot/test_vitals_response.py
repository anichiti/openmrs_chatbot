#!/usr/bin/env python3
"""Test full vitals history retrieval for doctor view"""

from database.db import OpenMRSDatabase
from collections import defaultdict

db = OpenMRSDatabase()

# Resolve patient identifier
patient_identifier = "100008E"
patient_info = db.verify_patient_exists(patient_identifier)

if patient_info:
    resolved_id = patient_info["patient_id"]
    print(f"Resolved {patient_identifier} to internal ID: {resolved_id}")
    
    # Get vitals history
    vitals_result = db.get_patient_vitals_history(resolved_id, limit=100)
    vitals_data = vitals_result.get("data", [])
    
    print(f"\nTotal vitals records (before dedup): {len(vitals_data)}")
    
    # Organize by date with DEDUPLICATION
    history_by_date = defaultdict(dict)
    
    # Mapping for deduplicating vital names (English versions take precedence)
    vital_normalization = {
        "Température (c)": "Temperature (c)",
        "Arterial blood oxygen saturation (pulse oximeter)": "SpO2",
    }
    
    for vital in vitals_data:
        vital_date = vital.get('obs_datetime', 'Unknown Date')
        vital_name = vital.get('vital_name', 'Unknown Vital')
        vital_value = vital.get('value_numeric') or vital.get('value_text', 'N/A')
        
        # Format the value
        if isinstance(vital_value, (int, float)):
            vital_value = f"{vital_value:.2f}" if isinstance(vital_value, float) else str(vital_value)
        
        # Normalize vital name
        if vital_name in vital_normalization:
            vital_name = vital_normalization[vital_name]
        
        # Only store if not already present
        if vital_name not in history_by_date[vital_date]:
            history_by_date[vital_date][vital_name] = vital_value
    
    print(f"Number of unique dates: {len(history_by_date)}")
    
    # Build response same as doctor view
    response = "## Vital Signs History (Past 10 Readings)\n\n"
    response += f"**Patient:** Joshua Johnson\n"
    response += f"**Patient ID:** {patient_identifier}\n\n"
    response += "### Timeline of Vital Measurements:\n\n"
    
    sorted_dates = sorted(history_by_date.keys(), reverse=True)
    total_vitals_after_dedup = 0
    for reading_date in sorted_dates:
        response += f"**{reading_date}**\n"
        vitals_at_date = history_by_date[reading_date]
        total_vitals_after_dedup += len(vitals_at_date)
        for vital_name, vital_value in sorted(vitals_at_date.items()):
            response += f"  - {vital_name}: {vital_value}\n"
        response += "\n"
    
    print(f"Total unique vitals after dedup: {total_vitals_after_dedup}")
    print("\nGenerated response:")
    print(response)
    print(f"\nResponse length: {len(response)} characters")

