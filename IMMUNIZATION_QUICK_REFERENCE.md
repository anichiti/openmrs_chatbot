# Immunization Feature - Quick Reference & Sample Queries

## Feature Overview
The immunization feature provides comprehensive vaccine history and recommendations for both patients and healthcare providers.

## Patient Queries (Patient-Friendly Language)

### Vaccine History
| Query | Response Contains |
|-------|-------------------|
| "What vaccines has my child received?" | Vaccination dates, vaccine names, patient age |
| "Show me the immunization history" | Complete history with dates |
| "What shots has my baby had?" | Previous vaccinations |

### Vaccine Recommendations
| Query | Response Contains |
|-------|-------------------|
| "What vaccines are due for my child?" | Upcoming vaccines, what they protect against, reactions |
| "Is my child up to date with vaccinations?" | Vaccination status, missing vaccines |
| "What immunizations does my baby need?" | Age-appropriate vaccines |
| "When should my child get the next vaccine?" | Next dose recommendations |

### Sample Patient Response
```
**Your Child's Immunization Record**
Patient: Joshua
Age: 5.4 years (65 months)

**Vaccines Your Child Has Received:**
1. **Immunizations**
   Given on: 2026-03-04 00:04:07

**Upcoming Vaccines for This Age:**
Your child is due for 5 vaccine(s):

1. **MMR (Measles, Mumps, Rubella)**
   What it protects against: Protects against measles, mumps, and rubella
   Number of doses needed: 2
   Interval between doses: 28 days minimum
   Common reactions: Fever, Rash, Mild joint pain in adults

**Important Information:**
• Bring this record to all health visits
• Vaccines protect your child from serious diseases
• Talk to your doctor about vaccine schedule
```

---

## Doctor Queries (Clinical Information)

### Patient Immunization Records
| Query | Response Contains |
|-------|-------------------|
| "Show me the immunization record for this patient" | Complete immunization history with clinical details |
| "What's the immunization schedule for this patient?" | Recommended vaccines with contraindications |
| "Check the immunization status for patient 100008E" | Full immunization report |
| "Review the vaccine history" | Historical data with clinical notes |
| "What vaccines are due for this patient?" | Clinical recommendations |

### Sample Doctor Response
```
IMMUNIZATION RECORD - PATIENT 100008E
Patient Name: Joshua
Age: 5.4 years (65 months)
================================================================================

IMMUNIZATION HISTORY:
1. Immunizations
   Date: 2026-03-04 00:04:07

RECOMMENDED UPCOMING VACCINES:
1. MMR (Measles, Mumps, Rubella)
   Recommended Age Group(s): 12-15 months, 4-6 years
   Total Doses Required: 2
   Dosing Interval: 28 days minimum
   Contraindications: Severe egg allergy, Immunocompromised, Pregnancy
   Common Side Effects: Fever, Rash, Mild joint pain in adults

CLINICAL CONSIDERATIONS:
• Verify immunization status against official vaccination schedule
• Check for any contraindications before administering vaccines
• Document vaccine lot numbers and administration sites
• Review catch-up vaccination if patient is behind schedule
```

---

## Supported Vaccines

| Vaccine | Common Names | Age Groups |
|---------|-------------|-----------|
| **MMR** | Measles, Mumps, Rubella | 12-15 months, 4-6 years |
| **COVID-19** | COVID vaccine, mRNA vaccine | 6 months and older |
| **DPT** | Diphtheria, Pertussis, Tetanus | 2+ months, booster every 10 years |
| **Polio IPV** | Polio vaccine, Inactivated polio | 2+ months, 4-6 years |
| **Influenza** | Seasonal flu, flu shot | 6 months and older (annual) |
| **DTaP** | Acellular pertussis version | 2 months+, 4-6 years |

---

## Feature Capabilities

### ✅ What Works

1. **Automatic Age Calculation**
   - Calculates patient age from birthdate
   - Shows age in both years and months
   - Updates recommendations based on age

2. **Immunization History Retrieval**
   - Pulls data from OpenMRS database
   - Shows vaccination dates
   - Lists vaccine names

3. **Smart Recommendations**
   - Recommends only age-appropriate vaccines
   - Excludes vaccines already given
   - Provides detailed dosing schedules

4. **Detailed Vaccine Information**
   - Number of doses required
   - Intervals between doses
   - Side effects and reactions
   - Contraindications
   - Efficacy data (for doctors)

5. **Dual-Format Responses**
   - **Patient format**: Simple, reassuring language with important reminders
   - **Doctor format**: Clinical details, contraindications, considerations

---

## How the Feature Works

### Data Flow
```
Patient Query about vaccines
        ↓
Triage Agent detects IMMUNIZATION_QUERY intent
        ↓
OpenMRS Database Query
├─ Find patient's internal ID
├─ Get patient birthdate
├─ Retrieve immunization history
└─ Load vaccine schedule database
        ↓
Age-Based Logic
├─ Calculate current age in months/years
├─ Match patient age to vaccine recommendations
└─ Exclude already-administered vaccines
        ↓
Format Response (Patient or Doctor)
        ↓
Return formatted response with:
- Vaccination history
- Recommended vaccines
- Important information
```

### Age-Based Vaccine Rules

- **2 months**: DPT, Polio IPV
- **4 months**: DPT, Polio IPV
- **6 months**: DPT, Polio IPV, Influenza, COVID-19
- **12-15 months**: MMR (first dose)
- **4-6 years**: MMR (second dose), Polio IPV, DPT, DTaP

---

## System Integration

### OpenMRS Tables Queried
- `patient` - Patient records
- `patient_identifier` - External patient IDs
- `person` - Birthdate information
- `obs` - Observation records (immunizations)

### Intent Detection
- **Intent Name**: `IMMUNIZATION_QUERY`
- **Agent**: `MCP_IMMUNIZATION_AGENT`
- **Detected Keywords**: vaccine, vaccination, immunization, shot, jab, MMR, DPT, schedule

### User Roles
- **PATIENT**: See simple language output
- **DOCTOR**: See clinical details

---

## Example Conversations

### Conversation 1: Parent Checking Vaccination Status
```
Parent: "Is my child up to date with vaccinations?"

System: [Detects IMMUNIZATION_QUERY]
        
Response: Your child (Joshua, 5.4 years) has received 4 vaccines.
Your child is due for 5 vaccines including MMR, COVID-19, DPT, Polio IPV, 
and seasonal Influenza. Contact your healthcare provider to schedule 
these vaccinations.

Important: Vaccines protect against serious diseases. Keep all records 
for school and travel.
```

### Conversation 2: Doctor Checking Immunization Record
```
Doctor: "Check the immunization status for patient 100008E"

System: [Detects IMMUNIZATION_QUERY]
        
Response: IMMUNIZATION RECORD - PATIENT 100008E

Patient: Joshua, 65 months (5.4 years)

Previous Vaccinations: 4 records found
- Last vaccination: 2026-03-04

Recommended Vaccines: 5 vaccines due
1. MMR - Check egg allergy before administering
2. COVID-19 - Age appropriate
3. DPT - Monitor for adverse reactions
4. Polio IPV - Standard schedule
5. Influenza - Annual

Clinical Considerations:
- Verify contraindications
- Document lot numbers
- Review catch-up vaccination needs
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No immunization found" | Patient may not have records in OpenMRS yet. First vaccination will create history. |
| "No vaccines recommended" | Patient may be up-to-date or too young/old for standard vaccines. Check age. |
| "Patient not found" | Verify patient ID (e.g., 100008E). Check patient exists in OpenMRS. |
| "Age calculation off" | Verify patient birthdate in OpenMRS person table. |

---

## Testing the Feature

### Quick Test
```bash
cd openmrs_chatbot
python ../test_immunization_feature.py
```

### Manual Test (Patient View)
```python
chatbot = ClinicalChatbot()
chatbot.user_role = "PATIENT"
result = chatbot.process_query(
    "What vaccines has my child received?",
    selected_patient_id='100008E'
)
print(result['response'])
```

### Manual Test (Doctor View)
```python
chatbot = ClinicalChatbot()
chatbot.user_role = "DOCTOR"
result = chatbot.process_query(
    "Show me the immunization record for this patient",
    selected_patient_id='100008E'
)
print(result['response'])
```

---

## Related Features

- **Vitals & Growth Metrics**: Monitor child's physical development
- **Medications**: Track active prescriptions
- **Allergies**: Important before vaccine administration
- **Patient Records**: Complete medical history

---

## File Locations

- **Fetcher**: `openmrs_chatbot/agents/immunization_openmrs_fetcher.py`
- **Response Formatter**: `openmrs_chatbot/agents/immunization_response.py`
- **Handler**: `openmrs_chatbot/main.py` (IMMUNIZATION_QUERY section)
- **Vaccine Data**: `openmrs_chatbot/data/immunization.json`
- **Tests**: `test_immunization_feature.py`
- **Documentation**: `IMMUNIZATION_FEATURE_IMPLEMENTATION.md`

