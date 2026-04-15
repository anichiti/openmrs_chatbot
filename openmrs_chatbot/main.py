import json
import os
from datetime import datetime
from agents.triage_agent import TriageAgent
from agents.two_layer_classifier import TwoLayerIntentClassifier
from agents.sql_agent import SQLAgent
from agents.mcp_agent import MCPAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.response_agent import ResponseAgent
from agents.validation_agent import ValidationAgent
from agents.drug_dosage_handler import detect_drug_intent, handle_drug_dosage_query, extract_drug_name, extract_drug_information, is_drug_approved
from agents.medication_openmrs_fetcher import MedicationOpenMRSFetcher
from agents.medication_response import MedicationResponseDoctor, MedicationResponsePatient
from agents.allergy_openmrs_fetcher import AllergyOpenMRSFetcher
from agents.allergy_response import AllergyResponseDoctor, AllergyResponsePatient
from agents.immunization_openmrs_fetcher import ImmunizationOpenMRSFetcher
from agents.immunization_response import ImmunizationResponseDoctor, ImmunizationResponsePatient
from agents.vitals_response import VitalsResponseDoctor, VitalsResponsePatient
from database.db import OpenMRSDatabase
from utils.logger import setup_logger
from utils.config import RESPONSES_FILE

logger = setup_logger(__name__)


class ClinicalChatbot:
    
    def __init__(self):
        logger.info("Initializing Clinical Chatbot...")
        self.triage_agent = TriageAgent()
        self.intent_classifier = TwoLayerIntentClassifier()  # 2-layer: keywords + embeddings
        self.sql_agent = SQLAgent()
        self.mcp_agent = MCPAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.response_agent = ResponseAgent()
        self.validation_agent = ValidationAgent()
        self.user_role = None  # Track user role for testing: 'doctor' or 'patient'
        self._cached_patient_id = None  # Cache patient data to avoid re-querying
        self._cached_patient_data = None
        logger.info("Chatbot initialized")
    
    @staticmethod
    def is_llm_allowed(intent):
        """
        CORE RULE: Gate function - LLM is only allowed for these intents:
        1. Intent classification fallback (Layer 3, <0.75 confidence)
        2. Response formatting (taking structured data dict → readable text)
        3. GENERAL_MEDICAL_QUERY only (when knowledge base is needed)
        
        LLM is BLOCKED for all other intents (pull from DB only):
        - VITALS_QUERY, PATIENT_RECORD_QUERY, MEDICATION_QUERY
        - MEDICATION_INFO_QUERY, ALLERGY_QUERY, IMMUNIZATION_QUERY
        - MILESTONE_QUERY, LAB_QUERY
        """
        allowed_intents = {
            "GENERAL_MEDICAL_QUERY",
            "MILESTONE_QUERY",
            "PATIENT_RECORD_QUERY",
        }
        
        if intent in allowed_intents:
            logger.info(f"LLM ALLOWED for intent: {intent}")
            return True
        else:
            logger.warning(f"LLM call blocked for intent {intent} — using database result only")
            return False
    
    def select_user_role(self):
        """Prompt user to select their role (doctor or patient) for testing"""
        print("\n" + "="*60)
        print("CLINICAL CHATBOT - USER ROLE SELECTION")
        print("="*60)
        print("Please select your role:")
        print("  1. Doctor")
        print("  2. Patient")
        print("="*60)
        
        while True:
            choice = input("\nEnter your choice (1 or 2): ").strip()
            if choice == "1":
                self.user_role = "DOCTOR"
                logger.info("User role selected: DOCTOR")
                print("\nYou are logged in as: DOCTOR")
                return
            elif choice == "2":
                self.user_role = "PATIENT"
                logger.info("User role selected: PATIENT")
                print("\nYou are logged in as: PATIENT")
                return
            else:
                print("[ERROR] Invalid choice. Please enter 1 or 2.")
    
    def format_full_name(self, patient):
        """Format patient full name from given_name and family_name"""
        given = patient.get('given_name', 'N/A')
        family = patient.get('family_name', 'N/A')
        if given != 'N/A' and family != 'N/A':
            return f"{given} {family}"
        elif given != 'N/A':
            return given
        elif family != 'N/A':
            return family
        return 'N/A'
    
    def _get_age_appropriate_reference_ranges(self, age_years):
        """
        ISSUE 7 FIX: Get age-appropriate reference ranges for vital signs.
        
        Returns a dict mapping vital names to their reference ranges based on patient age.
        All ranges in standard units.
        """
        ranges = {
            'temperature': ('36.1', '37.2', '°C'),  # Same for all ages
            'spo2': ('95', '100', '%'),  # Same for all ages
        }
        
        # Age-dependent ranges
        if age_years is None:
            # Default to adult ranges if age unknown
            age_years = 18
        
        if age_years <= 1:
            ranges.update({
                'blood_pressure': ('Systolic 80-110', 'Diastolic 50-80', 'mmHg'),
                'pulse': ('100-160', 'bpm'),
                'respiratory_rate': ('30-60', 'breaths/min'),
            })
        elif age_years <= 3:
            ranges.update({
                'blood_pressure': ('Systolic 80-110', 'Diastolic 50-80', 'mmHg'),
                'pulse': ('90-150', 'bpm'),
                'respiratory_rate': ('24-40', 'breaths/min'),
            })
        elif age_years <= 6:
            ranges.update({
                'blood_pressure': ('Systolic 85-120', 'Diastolic 55-80', 'mmHg'),
                'pulse': ('80-140', 'bpm'),
                'respiratory_rate': ('22-34', 'breaths/min'),
            })
        elif age_years <= 12:
            ranges.update({
                'blood_pressure': ('Systolic 85-120', 'Diastolic 55-80', 'mmHg'),
                'pulse': ('70-120', 'bpm'),
                'respiratory_rate': ('18-30', 'breaths/min'),
            })
        elif age_years <= 18:
            ranges.update({
                'blood_pressure': ('Systolic 95-130', 'Diastolic 60-85', 'mmHg'),
                'pulse': ('60-100', 'bpm'),
                'respiratory_rate': ('12-20', 'breaths/min'),
            })
        else:  # Adult 18+
            ranges.update({
                'blood_pressure': ('Systolic 90-120', 'Diastolic 60-80', 'mmHg'),
                'pulse': ('60-100', 'bpm'),
                'respiratory_rate': ('12-20', 'breaths/min'),
            })
        
        return ranges
    
    
    def is_direct_data_query(self, user_question, intent=None):
        """Detect if query is asking for simple/direct patient data (name, age, gender, address, vitals)
        
        Args:
            user_question: The user's question
            intent: The classified intent (optional) - used to exclude vital signs for medication queries
        
        Returns tuple: (is_direct, list_of_query_types)
        
        NOTE: If intent is MEDICATION_QUERY, excludes weight/vitals since those are used
        for dose calculation in the medication handler, not direct data return.
        NOTE: VITALS_HISTORY_QUERY is NOT a direct query - it needs special history formatting.
        NOTE: MEDICATION_EMERGENCY is NOT a direct query - it requires specialized emergency handler.
        """
        import re
        
        # EXCLUDE VITALS_HISTORY_QUERY: It should go to dedicated handler, not direct path
        if intent and intent.upper() == "VITALS_HISTORY_QUERY":
            return False, None
        
        # EXCLUDE MEDICATION_EMERGENCY: It requires specialized emergency handler, not direct data return
        if intent and intent.upper() == "MEDICATION_EMERGENCY":
            return False, None
        
        question_lower = user_question.lower().strip()
        
        # Patterns for each data type (ORDER MATTERS - check specific patterns first)
        direct_patterns = {
            'vitals_summary': ['vitals.*summary', 'vitals.*history', 'past.*vital', 'previous.*vital', 'vital.*reading', 'vital.*trend', 'history.*vital', 'all.*vital.*record'],
            'name': ['name', 'who is', 'called'],
            'age': ['age', 'how old', 'years old'],
            'gender': ['gender', 'sex', 'male or female'],
            'birthdate': ['birthdate', 'birth date', 'date of birth', 'dob', 'born when', 'when.*born'],
            'address': ['address', 'where.*live', 'location'],
            'city': ['which city', 'what city'],
            'state': ['which state', 'what state'],
            'vitals': ['vital signs', 'vitals', 'all vitals', 'full vitals', 'all observations', 'everything'],
            'bmi': ['\\bbmi\\b', 'body mass index'],
            'weight': ['weight', 'how much.*weigh', 'how heavy', 'how much does', 'what.*weigh', 'patient.*weigh'],
            'height': ['height', 'how tall', 'what.*tall', 'patient.*tall'],
            'temperature': ['temperature', 'temp', 'fever'],
            'blood_pressure': ['blood pressure', '\\bbp\\b', 'systolic', 'diastolic', 'systolic and diastolic', 'bp reading', 'blood pressure reading'],
            'heart_rate': ['heart rate', 'heartbeat', 'heart beat', 'pulse rate', 'pulse'],
            'spo2': ['oxygen', 'spo2', 'saturation', 'pulse ox', 'o2 sat', 'oxygen saturation', 'oxygen level', 'o2 level', 'oxygen reading', 'o2 reading'],
            'respiratory_rate': ['respiratory rate', 'breathing rate', 'respiration', 'breaths per minute', 'breath rate', '\\brr\\b', 'resp rate'],
            'conditions': ['condition', 'conditions', 'diagnos', 'medical condition', 'health condition'],
            'status': ['patient status', 'is.*deceased', 'is.*alive'],
        }
        
        matched_types = []
        for query_type, patterns in direct_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    matched_types.append(query_type)
                    break
        
        # MEDICATION QUERY FIX: If intent is MEDICATION_QUERY, exclude vital signs
        # because they're needed for dose calculation, not direct return
        if intent and intent.upper() == "MEDICATION_QUERY":
            vital_types = ['weight', 'height', 'temperature', 'blood_pressure', 'heart_rate', 'spo2', 'bmi', 'respiratory_rate']
            matched_types = [mt for mt in matched_types if mt not in vital_types]
        
        if matched_types:
            return True, matched_types
        
        return False, None
    
    def extract_direct_answer(self, query_type, patient_data):
        """Extract direct answer for simple data queries
        Returns the specific data point without extra formatting
        Handles both nested structure from query_patient_record and flat dicts
        """
        if not patient_data:
            return "No patient data available"
        
        # Extract flat patient record from nested structure if needed
        # query_patient_record returns {"patient": {"data": [...]}, "vitals": {"data": [...]}, ...}
        p = patient_data
        if isinstance(patient_data, dict) and "patient" in patient_data:
            patient_records = patient_data.get("patient", {}).get("data", [])
            if patient_records:
                p = patient_records[0]
            else:
                return "No patient data available"
        
        if query_type == 'name':
            full_name = self.format_full_name(p)
            return f"{full_name}"
        
        elif query_type == 'age':
            birthdate = p.get('birthdate', 'N/A')
            if birthdate and birthdate != 'N/A':
                try:
                    from datetime import datetime, date
                    if isinstance(birthdate, date):
                        birthdate_obj = birthdate
                    else:
                        birthdate_obj = datetime.strptime(str(birthdate).split()[0], "%Y-%m-%d").date()
                    today = date.today()
                    age = today.year - birthdate_obj.year
                    if (today.month, today.day) < (birthdate_obj.month, birthdate_obj.day):
                        age -= 1
                    return f"{age} years"
                except Exception as e:
                    logger.warning(f"Could not calculate age: {e}")
                    return "Age not available"
            return "Birthdate not available"
        
        elif query_type == 'gender':
            gender = p.get('gender', 'N/A')
            return f"{gender}"
        
        elif query_type == 'birthdate':
            birthdate = p.get('birthdate', 'N/A')
            return f"{birthdate}"
        
        elif query_type == 'address':
            address = p.get('address1', 'N/A')
            if address != 'N/A' and p.get('address2'):
                address += f", {p.get('address2')}"
            return f"{address}"
        
        elif query_type == 'city':
            city = p.get('city_village', 'N/A')
            return f"{city}"
        
        elif query_type == 'state':
            state = p.get('state_province', 'N/A')
            return f"{state}"
        
        elif query_type == 'status':
            if p.get('dead'):
                death_date = p.get('death_date', 'Unknown')
                return f"Deceased ({death_date})"
            else:
                return "Active"
        
        elif query_type == 'vitals_summary':
            # Extract ALL vitals history with timestamps from database
            try:
                # Get all vitals data (not just recent)
                all_vitals = patient_data.get("vitals", {}).get("data", []) if isinstance(patient_data, dict) and "vitals" in patient_data else []
                if not all_vitals:
                    return "No vital signs history available"
                
                # Group vitals by date/time to show all vitals recorded on same date together
                vitals_by_date = {}
                for vital in all_vitals:
                    vital_name = vital.get('vital_name', vital.get('concept_name', 'Unknown'))
                    vital_date = vital.get('obs_datetime', '') or vital.get('date_recorded', '')
                    value = vital.get('value_numeric') or vital.get('value_text', 'N/A')
                    
                    # Skip non-English names
                    if not all(ord(c) < 128 or c in '°²/' for c in vital_name):
                        continue
                    
                    if vital_date not in vitals_by_date:
                        vitals_by_date[vital_date] = []
                    
                    vitals_by_date[vital_date].append({
                        'name': vital_name,
                        'value': value
                    })
                
                # Format output: show all vitals from each date grouped together
                parts = ["**VITAL SIGNS HISTORY**\n"]
                
                # Sort by date (most recent first)
                sorted_dates = sorted(vitals_by_date.keys(), reverse=True)
                
                for vital_date in sorted_dates:
                    readings = vitals_by_date[vital_date]
                    parts.append(f"**{vital_date}:**")
                    for reading in readings:
                        parts.append(f"  • {reading['name']}: {reading['value']}")
                    parts.append("")  # Blank line between date groups
                
                return "\n".join(parts)
            except Exception as e:
                logger.error(f"Error formatting vitals summary: {e}")
                return "Error retrieving vitals history"
        
        elif query_type == 'vitals':
            # Extract vitals from the nested structure
            vitals_data = patient_data.get("vitals", {}).get("data", []) if isinstance(patient_data, dict) and "vitals" in patient_data else []
            if not vitals_data:
                return "No vital signs available"
            
            # Debug: Log what fields are in the first vital record
            if vitals_data:
                logger.debug(f"DEBUG - First vital record keys: {list(vitals_data[0].keys())}")
                logger.debug(f"DEBUG - First vital record: {vitals_data[0]}")
            
            # Find the most recent timestamp to filter only recent vitals
            most_recent_date = None
            for vital in vitals_data:
                vital_date = vital.get('obs_datetime', '') or vital.get('date_recorded', '')
                if vital_date and (not most_recent_date or vital_date > most_recent_date):
                    most_recent_date = vital_date
            
            # Filter vitals to only show those from the most recent timestamp
            recent_vitals = []
            if most_recent_date:
                recent_vitals = [v for v in vitals_data if (v.get('obs_datetime', '') or v.get('date_recorded', '')) == most_recent_date]
            else:
                recent_vitals = vitals_data
            
            parts = []
            seen = set()
            height_cm = None
            weight_kg = None
            for vital in recent_vitals:
                vital_name = vital.get('vital_name', vital.get('concept_name', 'Unknown'))
                # Skip non-English duplicates
                if not all(ord(c) < 128 or c in '°²/' for c in vital_name):
                    continue
                if vital_name.lower() in seen:
                    continue
                seen.add(vital_name.lower())
                value = vital.get('value_numeric') or vital.get('value_text', 'N/A')
                parts.append(f"  {vital_name}: {value}")
                # Track height/weight for BMI calculation
                if 'height' in vital_name.lower() and vital.get('value_numeric'):
                    height_cm = vital.get('value_numeric')
                if 'weight' in vital_name.lower() and vital.get('value_numeric'):
                    weight_kg = vital.get('value_numeric')
            # Calculate BMI if height and weight available but BMI not in data
            if height_cm and weight_kg and not any('bmi' in p.lower() for p in parts):
                bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
                parts.append(f"  BMI (calculated): {bmi} kg/m²")
            
            # Add timestamp if available
            if most_recent_date:
                result = "\n".join(parts) if parts else "No vital signs available"
                result += f"\n\nRecorded: {most_recent_date}"
                return result
            else:
                return "\n".join(parts) if parts else "No vital signs available"
        
        elif query_type == 'bmi':
            # Calculate BMI from height and weight
            vitals_data = patient_data.get("vitals", {}).get("data", []) if isinstance(patient_data, dict) and "vitals" in patient_data else []
            height_cm = None
            weight_kg = None
            for vital in vitals_data:
                vital_name = vital.get('vital_name', vital.get('concept_name', '')).lower()
                if 'height' in vital_name and vital.get('value_numeric'):
                    height_cm = vital.get('value_numeric')
                if 'weight' in vital_name and vital.get('value_numeric'):
                    weight_kg = vital.get('value_numeric')
                if 'bmi' in vital_name and vital.get('value_numeric'):
                    return f"BMI: {vital.get('value_numeric')} kg/m²"
            if height_cm and weight_kg:
                bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
                return f"BMI: {bmi} kg/m² (calculated from Height: {height_cm} cm, Weight: {weight_kg} kg)"
            return "BMI not available (missing height or weight data)"
        
        elif query_type == 'conditions':
            # Extract conditions from the nested structure
            conditions_data = patient_data.get("conditions", {}).get("data", []) if isinstance(patient_data, dict) and "conditions" in patient_data else []
            if not conditions_data:
                return "No conditions/diagnoses recorded for this patient"
            parts = ["Conditions/Diagnoses:"]
            for cond in conditions_data:
                cond_name = cond.get('condition_name', 'Unknown')
                onset = cond.get('onset_date', '')
                end = cond.get('end_date', '')
                status = "Active" if not end else f"Resolved ({str(end)[:10]})"
                onset_str = f" (onset: {str(onset)[:10]})" if onset else ""
                parts.append(f"  • {cond_name} - {status}{onset_str}")
            return "\n".join(parts)
        
        elif query_type in ('weight', 'height', 'temperature', 'blood_pressure', 'heart_rate', 'spo2', 'respiratory_rate'):
            # Individual vital sign lookups
            vitals_data = patient_data.get("vitals", {}).get("data", []) if isinstance(patient_data, dict) and "vitals" in patient_data else []
            
            # Find the most recent timestamp to filter only recent vitals
            most_recent_date = None
            for vital in vitals_data:
                vital_date = vital.get('obs_datetime', '') or vital.get('date_recorded', '')
                if vital_date and (not most_recent_date or vital_date > most_recent_date):
                    most_recent_date = vital_date
            
            # Filter vitals to only show those from the most recent timestamp
            recent_vitals = []
            if most_recent_date:
                recent_vitals = [v for v in vitals_data if (v.get('obs_datetime', '') or v.get('date_recorded', '')) == most_recent_date]
            else:
                recent_vitals = vitals_data
            
            # Calculate patient age for reference ranges (Issue 7)
            age_years = None
            if isinstance(patient_data, dict) and patient_data.get("patient", {}).get("data"):
                p = patient_data.get("patient", {}).get("data", [{}])[0]
                birthdate = p.get('birthdate')
                if birthdate:
                    try:
                        from datetime import datetime, date
                        if isinstance(birthdate, date):
                            birthdate_obj = birthdate
                        else:
                            birthdate_obj = datetime.strptime(str(birthdate).split()[0], "%Y-%m-%d").date()
                        today = date.today()
                        age_years = today.year - birthdate_obj.year
                        if (today.month, today.day) < (birthdate_obj.month, birthdate_obj.day):
                            age_years -= 1
                    except Exception as e:
                        logger.debug(f"Could not calculate age for reference ranges: {e}")
            
            # Get age-appropriate reference ranges (Issue 7)
            ref_ranges = self._get_age_appropriate_reference_ranges(age_years)
            
            vital_name_map = {
                'weight': ['weight'],
                'height': ['height'],
                'temperature': ['temperature', 'temp'],
                'blood_pressure': ['blood pressure', 'systolic', 'diastolic'],
                'heart_rate': ['heart rate', 'heartbeat', 'heart beat', 'pulse rate', 'pulse'],
                'spo2': ['oxygen saturation', 'spo2', 'blood oxygen'],
                'respiratory_rate': ['respiratory rate', 'breathing rate', 'respiration', 'breaths per minute'],
            }
            search_terms = vital_name_map.get(query_type, [])
            matches = []
            
            # Special handling for blood pressure to avoid duplication
            if query_type == 'blood_pressure':
                systolic_val = None
                diastolic_val = None
                
                for vital in recent_vitals:
                    vname = vital.get('vital_name', vital.get('concept_name', '')).lower()
                    if 'systolic' in vname:
                        systolic_val = vital.get('value_numeric')
                    elif 'diastolic' in vname:
                        diastolic_val = vital.get('value_numeric')
                
                # Format BP reading with reference ranges
                if systolic_val is not None or diastolic_val is not None:
                    if systolic_val is not None and diastolic_val is not None:
                        bp_reading = f"Blood Pressure: {systolic_val}/{diastolic_val} mmHg"
                    elif systolic_val is not None:
                        bp_reading = f"Blood Pressure (Systolic): {systolic_val} mmHg"
                    else:
                        bp_reading = f"Blood Pressure (Diastolic): {diastolic_val} mmHg"
                    
                    matches.append(bp_reading)
                    
                    # Add reference ranges (but only once, not duplicated)
                    if query_type in ref_ranges:
                        ref_info = ref_ranges[query_type]
                        if isinstance(ref_info, tuple) and len(ref_info) >= 3:
                            matches.append(f"  {ref_info[0]} {ref_info[2]}")
                            matches.append(f"  {ref_info[1]} {ref_info[2]}")
            else:
                # First try to find in recent vitals (same date as most recent)
                for vital in recent_vitals:
                    vname = vital.get('vital_name', vital.get('concept_name', '')).lower()
                    if any(term in vname for term in search_terms):
                        value = vital.get('value_numeric') or vital.get('value_text', 'N/A')
                        display_name = vital.get('vital_name', vital.get('concept_name', 'Unknown'))
                        # Skip non-English duplicates
                        if all(ord(c) < 128 or c in '°²/' for c in display_name):
                            # Append reference range (Issue 7)
                            if query_type in ref_ranges:
                                ref_info = ref_ranges[query_type]
                                if isinstance(ref_info, tuple) and len(ref_info) >= 2:
                                    # Standard format: (min, max, unit)
                                    ref_range = f"{ref_info[0]}-{ref_info[1]} {ref_info[2]}"
                                    matches.append(f"{display_name}: {value} {ref_info[2]}  (Reference: {ref_range})")
                                else:
                                    matches.append(f"{display_name}: {value}")
                            else:
                                matches.append(f"{display_name}: {value}")
            
            # If not found in recent vitals, look for most recent historical value
            if not matches:
                if query_type == 'blood_pressure':
                    systolic_val = None
                    diastolic_val = None
                    
                    for vital in vitals_data:
                        vname = vital.get('vital_name', vital.get('concept_name', '')).lower()
                        if 'systolic' in vname:
                            systolic_val = vital.get('value_numeric')
                        elif 'diastolic' in vname:
                            diastolic_val = vital.get('value_numeric')
                    
                    if systolic_val is not None or diastolic_val is not None:
                        if systolic_val is not None and diastolic_val is not None:
                            bp_reading = f"Blood Pressure: {systolic_val}/{diastolic_val} mmHg"
                        elif systolic_val is not None:
                            bp_reading = f"Blood Pressure (Systolic): {systolic_val} mmHg"
                        else:
                            bp_reading = f"Blood Pressure (Diastolic): {diastolic_val} mmHg"
                        
                        matches.append(bp_reading)
                        if query_type in ref_ranges:
                            ref_info = ref_ranges[query_type]
                            if isinstance(ref_info, tuple) and len(ref_info) >= 3:
                                matches.append(f"  {ref_info[0]} {ref_info[2]}")
                                matches.append(f"  {ref_info[1]} {ref_info[2]}")
                else:
                    for vital in vitals_data:
                        vname = vital.get('vital_name', vital.get('concept_name', '')).lower()
                        if any(term in vname for term in search_terms):
                            value = vital.get('value_numeric') or vital.get('value_text', 'N/A')
                            display_name = vital.get('vital_name', vital.get('concept_name', 'Unknown'))
                            vital_date = vital.get('obs_datetime', '') or vital.get('date_recorded', '')
                            # Skip non-English duplicates
                            if all(ord(c) < 128 or c in '°²/' for c in display_name):
                                matches.append(f"{display_name}: {value}")
                                if vital_date:
                                    matches.append(f"  (Previous recording: {vital_date})")
                            break  # Take only the first (most recent) match
            
            if matches:
                result = "\n".join(matches)
                if most_recent_date:
                    result += f"\n\nRecorded: {most_recent_date}"
                return result
            return f"{query_type.replace('_', ' ').title()} not available"
        
        return "Data not available"
    
    def format_response(self, response_dict):
        """Format response dictionary into readable text"""
        if isinstance(response_dict, dict):
            parts = []
            if response_dict.get("answer"):
                parts.append(f"Answer:\n{response_dict['answer']}")
            if response_dict.get("when_to_see_doctor"):
                parts.append(f"\nWhen to See Doctor:\n{response_dict['when_to_see_doctor']}")
            if response_dict.get("confidence"):
                confidence = response_dict['confidence']
                parts.append(f"\nConfidence: {confidence}")
            return "\n".join(parts)
        return str(response_dict)

    def process_query(self, user_question, selected_patient_id=None):
        """Process user query - routes to doctor or patient pipeline.
        
        Architecture:
        1. Common setup: intent classification, patient data fetch, direct data fast path
        2. Route to _doctor_pipeline() or _patient_pipeline() based on session role
        3. Each pipeline handles MEDICATION_QUERY differently, delegates others to _handle_shared_intents()
        4. KB + LLM response only runs for intents that need it (MILESTONE, PATIENT_RECORD, GENERAL)
        """
        logger.info(f"Query received: {user_question}")
        
        # USE 2-LAYER CLASSIFIER: keywords (fast) → embeddings (accurate)
        # Intent classification is role-agnostic; role handling happens in doctor/patient pipelines
        classification_result = self.intent_classifier.classify(user_question)
        intent = classification_result["intent"]
        confidence = classification_result["confidence"]
        layer_used = classification_result["layer_used"]
        
        patient_id = selected_patient_id or self.triage_agent.extract_patient_id(user_question)
        user_type = self.user_role if self.user_role else "PATIENT"
        logger.info(f"[PIPELINE] Role: {user_type} | Intent: {intent} (confidence: {confidence:.2f}, layer: {layer_used}) | Patient: {patient_id or 'N/A'}")

        context_data = {
            "sources": [],
            "kb_content": "",
            "patient_data": None,
            "mcp_data": {},
            "db_error": None
        }

        # ====================================================================
        # COMMON: Fetch patient data (shared by both pipelines)
        # ====================================================================
        if patient_id:
            is_direct, query_type = self.is_direct_data_query(user_question, intent=intent)
            try:
                if self._cached_patient_id == patient_id and self._cached_patient_data:
                    patient_data = self._cached_patient_data
                    logger.info(f"Using cached patient data for ID: {patient_id}")
                else:
                    patient_data = self.sql_agent.query_patient_record(patient_id)
                    self._cached_patient_id = patient_id
                    self._cached_patient_data = patient_data
                    logger.info(f"Patient record fetched and cached for ID: {patient_id}")
                if patient_data and patient_data.get("patient", {}).get("data"):
                    context_data["patient_data"] = patient_data
                    context_data["sources"] = ["Patient Record (OpenMRS)"]
                    logger.info(f"Patient record retrieved for ID: {patient_id}")
                    
                    # Fast path: direct data queries return instantly without LLM
                    if is_direct and query_type:
                        answers = []
                        for qt in query_type:
                            ans = self.extract_direct_answer(qt, patient_data)
                            if ans and ans not in ("No patient data available", "Data not available"):
                                answers.append(ans)
                        direct_answer = "\n".join(answers) if answers else None
                        if direct_answer:
                            logger.info(f"Direct data query ({query_type}): returning instant answer")
                            result = {
                                "timestamp": datetime.now().isoformat(),
                                "user_type": user_type,
                                "intent": intent,
                                "question": user_question,
                                "response": direct_answer,
                                "sources": ["Patient Record (OpenMRS)"],
                                "patient_id": patient_id
                            }
                            self.save_response(result)
                            return result
                else:
                    context_data["db_error"] = "No patient data found"
                    logger.warning(f"No patient data found for ID: {patient_id}")
            except Exception as e:
                logger.error(f"Error querying patient record: {e}")
                context_data["db_error"] = str(e)

        # ====================================================================
        # ROUTE TO APPROPRIATE PIPELINE
        # ====================================================================
        # Single intent classification (embedding-based, more accurate)
        if user_type.upper() == "DOCTOR":
            return self._doctor_pipeline(user_question, intent, patient_id, context_data, user_type)
        else:
            return self._patient_pipeline(user_question, intent, patient_id, context_data, user_type)

    # ====================================================================
    # SCOPE DEFINITIONS: What each pipeline is allowed to handle
    # ====================================================================
    DOCTOR_ALLOWED_INTENTS = {
        'DRUG_INFORMATION_QUERY',          # FDA/RxNorm drug info: side effects, contraindications, warnings
        'MEDICATION_QUERY',                # Drug dosage calculation, drug info from APIs
        'PAST_MEDICATIONS_QUERY',          # Full medication history
        'ALLERGY_QUERY',                   # Clinical allergy profile + contraindication check
        'MEDICATION_INFO_QUERY',           # What's been prescribed (full details)
        'MEDICATION_EMERGENCY',             # Clinical emergency guidance
        'MEDICATION_COMPATIBILITY_QUERY',  # Drug interactions
        'MEDICATION_ADMINISTRATION_QUERY', # Administration details
        'MEDICATION_SIDE_EFFECTS_QUERY',   # Side effects from API data
        'VITALS_QUERY',                    # Full clinical vitals
        'VITALS_HISTORY_QUERY',            # Past vitals history with trends
        'LAB_QUERY',                       # Lab orders and results
        'ENCOUNTERS_QUERY',                # Patient visits and encounters
        'FUTURE_APPOINTMENTS_QUERY',       # Upcoming scheduled appointments
        'IMMUNIZATION_QUERY',              # Immunization records + clinical assessment
        'MILESTONE_QUERY',                 # Developmental milestones
        'PATIENT_RECORD_QUERY',            # Full patient record access
    }

    PATIENT_ALLOWED_INTENTS = {
        'DRUG_INFORMATION_QUERY',          # FDA/RxNorm drug info in patient-friendly language
        'MEDICATION_QUERY',                # Active meds list only (dosage blocked)
        'PAST_MEDICATIONS_QUERY',          # Simplified medication history
        'ALLERGY_QUERY',                   # Allergy history (simplified)
        'MEDICATION_INFO_QUERY',           # What meds is my child on
        'MEDICATION_EMERGENCY',             # Redirect to emergency services
        'MEDICATION_COMPATIBILITY_QUERY',  # "Consult your doctor"
        'MEDICATION_ADMINISTRATION_QUERY', # How to give medication
        'MEDICATION_SIDE_EFFECTS_QUERY',   # General side effects info
        'VITALS_QUERY',                    # Simplified vitals (growth info)
        'VITALS_HISTORY_QUERY',            # Past vitals history (simplified for patient)
        'LAB_QUERY',                       # Lab results (patient-friendly format)
        'ENCOUNTERS_QUERY',                # Visit history (patient-friendly format)
        'FUTURE_APPOINTMENTS_QUERY',       # Upcoming appointments (patient-friendly)
        'IMMUNIZATION_QUERY',              # Vaccination history + what's due + missed
        'MILESTONE_QUERY',                 # Age-appropriate milestone tracking
        'PATIENT_RECORD_QUERY',            # Demographics (age, name, gender)
    }

    # ====================================================================
    # ALLERGY SAFETY NET — Option B
    # If ANY response mentions a drug and a patient is loaded, append allergy status.
    # This catches queries that bypassed the ALLERGY_QUERY intent entirely.
    # ====================================================================
    def _allergy_safety_net(self, result, user_question, patient_id, context_data, user_type):
        """CHANGE 5: Allergy Auto-Check After Every Handler.
        
        Post-process any result: scan combined query+response for drug names matching patient allergies.
        Runs after every handler for ALL intents.
        - Scans query + response text combined (case insensitive)
        - Compares against patient's allergy list from database
        - Matches on drug name (word boundaries)
        - If match found: prepends warning from warning_engine.py
        - If no allergies recorded: skips entirely (no "no allergies" message)
        
        FIX: Secondary trigger for contraindication queries (Issue 5)
        - If query contains contraindication phrases, show complete allergy profile
        - Contraindication phrases: "should not be given", "cannot take", "avoid", etc.
        """
        import re as _re
        from utils.warning_engine import warning_allergy_match
        
        # Skip if no patient or if allergy was already checked
        if not patient_id:
            return result
        intent = result.get("intent", "")
        if intent == "ALLERGY_QUERY":
            return result  # Already handled
        # Skip if this was a prescribe/safety check in MEDICATION_QUERY (already has allergy)
        if intent == "MEDICATION_QUERY" and ("ALLERGY CHECK" in result.get("response", "") or "[ALERT]" in result.get("response", "")):
            return result

        logger.info(f"[CHANGE 5 ALLERGY SAFETY NET] Scanning query + response for allergies (intent: {intent})")
        try:
            # Fetch patient's allergy list from database
            allergy_fetcher = AllergyOpenMRSFetcher()
            allergies = allergy_fetcher.get_patient_allergies(patient_id)
            allergy_fetcher.disconnect()
            
            # If no allergies recorded, skip entirely (don't show message)
            if not allergies:
                logger.info(f"[CHANGE 5 ALLERGY SAFETY NET] No allergies recorded - skipping entirely")
                return result
            
            # Extract allergen list (drug names, food, environment)
            allergen_list = []
            allergies_by_type = allergies.get("allergies_by_type", {})
            for allergen_type, allergen_items in allergies_by_type.items():
                for allergen_info in allergen_items:
                    allergen_name = allergen_info.get("allergen_name", "")
                    if allergen_name:
                        allergen_list.append(allergen_name.lower())
            
            if not allergen_list:
                logger.info(f"[CHANGE 5 ALLERGY SAFETY NET] No allergens found in patient records")
                return result
            
            # Combine query + response text for scanning
            combined_text = (user_question + " " + result.get("response", "")).lower()
            
            # SECONDARY TRIGGER: Check for contraindication queries (Issue 5)
            contraindication_triggers = [
                "should not be given", "cannot take", "avoid", "not give",
                "unsafe", "contraindicated", "allergic to", "safe to give",
                "safe to prescribe", "anything to avoid", "what to avoid",
                "cannot have", "should avoid", "not allowed", "restricted"
            ]
            
            has_contraindication_trigger = any(trigger in combined_text for trigger in contraindication_triggers)
            
            # Scan combined text for matches against allergen list (case insensitive, word boundaries)
            matched_allergens = []
            for allergen in allergen_list:
                pattern = r'\b' + _re.escape(allergen) + r'\b'
                if _re.search(pattern, combined_text):
                    matched_allergens.append(allergen)
            
            # If matches found OR contraindication trigger is present, show allergy profile
            if matched_allergens:
                logger.warning(f"[CHANGE 5 ALLERGY SAFETY NET] Matched allergens: {matched_allergens}")
                
                # Check first matched allergen for contraindication details
                try:
                    allergy_fetcher2 = AllergyOpenMRSFetcher()
                    allergy_check = allergy_fetcher2.check_drug_allergy(patient_id, matched_allergens[0])
                    allergy_fetcher2.disconnect()
                    
                    if allergy_check.get('is_contraindicated'):
                        # Use warning_engine to generate warning
                        warning_text = warning_allergy_match(
                            allergy_check,
                            matched_allergens[0],
                            role=user_type.lower() if user_type else "patient"
                        )
                        # Prepend warning to response
                        result["response"] = warning_text + "\n\n" + result["response"]
                        result["sources"] = list(set(result.get("sources", []) + ["Allergy Safety Net"]))
                        logger.warning(f"[CHANGE 5 ALLERGY SAFETY NET] WARNING prepended for {matched_allergens[0]}")
                except Exception as e:
                    logger.error(f"[CHANGE 5 ALLERGY SAFETY NET] Error checking contraindication: {e}")
            elif has_contraindication_trigger:
                # SECONDARY TRIGGER: Show complete allergy profile for contraindication queries
                logger.info(f"[CHANGE 5 ALLERGY SAFETY NET] Contraindication trigger detected - showing full allergy profile")
                
                try:
                    # Build complete allergy profile
                    allergy_profile = "**PATIENT ALLERGY PROFILE**\n\n"
                    has_allergies = False
                    
                    for allergen_type, allergen_items in allergies_by_type.items():
                        if allergen_items:
                            has_allergies = True
                            allergy_profile += f"**{allergen_type.title()}:**\n"
                            for allergen_info in allergen_items:
                                allergen_name = allergen_info.get("allergen_name", "Unknown")
                                severity = allergen_info.get("severity", "Unknown")
                                allergy_profile += f"  • {allergen_name} (Severity: {severity})\n"
                            allergy_profile += "\n"
                    
                    if has_allergies:
                        allergy_profile += "**Note:** Always verify patient allergies before administering any substance.\n"
                        result["response"] = allergy_profile + "\n\n" + result["response"]
                        result["sources"] = list(set(result.get("sources", []) + ["Allergy Profile"]))
                        logger.info(f"[CHANGE 5 ALLERGY SAFETY NET] Complete allergy profile prepended")
                except Exception as e:
                    logger.error(f"[CHANGE 5 ALLERGY SAFETY NET] Error building allergy profile: {e}")
            else:
                logger.info(f"[CHANGE 5 ALLERGY SAFETY NET] No allergen matches in query+response")
            
            return result

        except Exception as e:
            logger.error(f"[CHANGE 5 ALLERGY SAFETY NET] Error during scan: {e}")
            return result

    # ====================================================================
    # DOCTOR PIPELINE
    # ====================================================================
    def _doctor_pipeline(self, user_question, intent, patient_id, context_data, user_type):
        """Doctor pipeline: clinical-grade processing with full API access."""
        logger.info(f"[DOCTOR PIPELINE] Processing intent: {intent}")

        # SCOPE GUARD: Block out-of-scope intents
        if intent not in self.DOCTOR_ALLOWED_INTENTS:
            logger.info(f"[DOCTOR PIPELINE] Intent '{intent}' out of scope")
            return self._out_of_scope_response(user_question, intent, patient_id, user_type, role="doctor")

        if intent == "MEDICATION_QUERY":
            result = self._doctor_medication_handler(user_question, patient_id, context_data, user_type)
            if result:
                return result

        if intent == "DRUG_INFORMATION_QUERY":
            result = self._doctor_drug_information_handler(user_question, user_type)
            if result:
                return result

        # Delegate to shared intent handler for all other allowed intents
        result = self._handle_shared_intents(user_question, intent, patient_id, context_data, user_type)

        # SAFETY NET: Always check allergies if a drug name is detected
        return self._allergy_safety_net(result, user_question, patient_id, context_data, user_type)

    # ====================================================================
    # PATIENT PIPELINE
    # ====================================================================
    def _patient_pipeline(self, user_question, intent, patient_id, context_data, user_type):
        """Patient/Parent pipeline: safety-first with user-friendly responses."""
        logger.info(f"[PATIENT PIPELINE] Processing intent: {intent}")

        # SCOPE GUARD: Block out-of-scope intents
        if intent not in self.PATIENT_ALLOWED_INTENTS:
            logger.info(f"[PATIENT PIPELINE] Intent '{intent}' out of scope")
            return self._out_of_scope_response(user_question, intent, patient_id, user_type, role="patient")

        if intent == "MEDICATION_QUERY":
            result = self._patient_medication_handler(user_question, patient_id, context_data, user_type)
            if result:
                return result

        if intent == "DRUG_INFORMATION_QUERY":
            result = self._patient_drug_information_handler(user_question, user_type)
            if result:
                return result

        # Delegate to shared intent handler for all other allowed intents
        result = self._handle_shared_intents(user_question, intent, patient_id, context_data, user_type)

        # SAFETY NET: Always check allergies if a drug name is detected
        return self._allergy_safety_net(result, user_question, patient_id, context_data, user_type)

    # ====================================================================
    # DOCTOR MEDICATION HANDLER
    # ====================================================================
    def _doctor_medication_handler(self, user_question, patient_id, context_data, user_type):
        """Doctor-specific medication processing.
        
        Flow:
        0. Extract drug name from question
        1. Decide query type: prescribe/safety check vs dose calculation
        2. PRESCRIBE/SAFETY QUERY (no dose keyword): allergy check only
        3. Active medication list query
        4. DOSE QUERY (dose keyword present): allergy check + dose calculation
        5. MCP fallback
        """
        logger.info("[DOCTOR MED] Doctor medication query handler activated")
        
        # 0. Extract drug name and classify query type
        drug_name_for_check = extract_drug_name(user_question)
        query_lower = user_question.lower()
        
        # Dose-specific keywords — only these trigger dose calculation
        dose_keywords = [r'\bdose\b', r'\bdosage\b', r'\bhow\s+much', r'\bwhat\s+dose',
                         r'\bwhat\s+amount', r'\bmg\b', r'\b\d+mg\b']
        import re as _re
        is_dose_query = any(_re.search(kw, query_lower) for kw in dose_keywords)
        
        # Prescribe/safety keywords — allergy check only, no dose
        prescribe_keywords = ['prescribe', 'safe', 'give', 'administer', 'can i', 'should i', 'ok to']
        is_prescribe_query = any(kw in query_lower for kw in prescribe_keywords)
        
        logger.info(f"[DOCTOR MED] drug='{drug_name_for_check}', is_dose_query={is_dose_query}, is_prescribe_query={is_prescribe_query}")
        
        # 1. PRESCRIBE/SAFETY QUERY — allergy check ONLY (no dose calculation)
        if is_prescribe_query and not is_dose_query and drug_name_for_check and patient_id:
            logger.info(f"[DOCTOR MED] Prescribe/safety query — running allergy check only for '{drug_name_for_check}'")
            try:
                allergy_fetcher = AllergyOpenMRSFetcher()
                allergy_check = allergy_fetcher.check_drug_allergy(patient_id, drug_name_for_check)
                allergy_fetcher.disconnect()
                
                self._ensure_patient_data(patient_id, context_data)
                patient_name = self._get_patient_name(context_data)
                response = AllergyResponseDoctor.format_drug_allergy_check(
                    drug_name_for_check, allergy_check, patient_id, patient_name
                )
                return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                        ["Allergy Check + OpenMRS Records"], patient_id)
            except Exception as e:
                logger.error(f"[DOCTOR MED] Allergy check error: {e}")
        
        # 2. Active medication list query
        active_med_keywords = ['active', 'current', 'taking', 'prescribed', 'using', 'on', 'receives', 'getting', 'medications', 'medicine']
        is_active_med_query = any(kw in query_lower for kw in active_med_keywords)
        
        if is_active_med_query and patient_id:
            logger.info(f"[DOCTOR MED] Active medications query for patient {patient_id}")
            try:
                med_fetcher = MedicationOpenMRSFetcher()
                active_medications = med_fetcher.get_active_medications(patient_id)
                med_fetcher.disconnect()
                
                if active_medications:
                    self._ensure_patient_data(patient_id, context_data)
                    patient_name = self._get_patient_name(context_data)
                    response = MedicationResponseDoctor.format_active_medications(
                        active_medications, patient_id, patient_name
                    )
                    return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                            ["Active Medications + OpenMRS Records"], patient_id)
                else:
                    logger.info(f"[DOCTOR MED] No active medications found for patient {patient_id}")
                    return self._build_result(user_type, "MEDICATION_QUERY", user_question,
                                            f"Patient {patient_id} currently has no active medications.",
                                            ["OpenMRS Records"], patient_id)
            except Exception as e:
                logger.error(f"[DOCTOR MED] Error fetching active medications: {e}")
        
        # 2.5. Drug information query (indications, contraindications, side effects, warnings, etc.)
        drug_info_keywords = ['indication', 'contraindication', 'warning', 'precaution',
                             'adverse effect', 'side effect', 'drug interaction',
                             'properties', 'information about']
        is_drug_info_query = any(kw in query_lower for kw in drug_info_keywords)
        
        if is_drug_info_query:
            drug_name = extract_drug_name(user_question)
            if drug_name:
                logger.info(f"[DOCTOR MED] Drug info query for '{drug_name}' - fetching from KB + FDA API")
                try:
                    info_response = extract_drug_information(user_question, drug_name)
                    if info_response:
                        response = (
                            f"**Drug Information: {drug_name.title()}**\n\n"
                            f"{info_response}\n\n"
                            "**Sources:** FDA OpenFDA API, WHO Analgesics/Antipyretics/NSAIDs KB, RxNorm\n"
                            "**Note:** Always review current clinical guidelines and patient-specific factors."
                        )
                        return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                                ["Drug Knowledge Base", "FDA OpenFDA API"], patient_id)
                except Exception as e:
                    logger.error(f"[DOCTOR MED] Error fetching drug information: {e}")
        
        # 3. DOSE QUERY — allergy pre-check then dose calculation
        self._ensure_patient_data(patient_id, context_data)
        
        drug_intent = detect_drug_intent(user_question)
        logger.info(f"[DOCTOR MED] drug_intent={drug_intent}, has_patient_data={bool(context_data.get('patient_data'))}")
        
        allergy_safety_note = ""
        if is_dose_query and drug_name_for_check and patient_id:
            logger.info(f"[DOCTOR MED] Dose query — running allergy pre-check for '{drug_name_for_check}'")
            try:
                allergy_fetcher = AllergyOpenMRSFetcher()
                allergy_check = allergy_fetcher.check_drug_allergy(patient_id, drug_name_for_check)
                allergy_fetcher.disconnect()
                
                if allergy_check.get('is_contraindicated'):
                    logger.warning(f"[DOCTOR MED] CONTRAINDICATED: {drug_name_for_check} for patient {patient_id}")
                    patient_name = self._get_patient_name(context_data)
                    response = AllergyResponseDoctor.format_drug_allergy_check(
                        drug_name_for_check, allergy_check, patient_id, patient_name
                    )
                    return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                            ["Allergy Check + OpenMRS Records"], patient_id)
                else:
                    allergy_safety_note = (
                        f"ALLERGY CHECK: No documented allergy to {drug_name_for_check} for this patient. "
                        f"Safe to proceed.\n\n"
                    )
                    logger.info(f"[DOCTOR MED] Allergy pre-check PASSED for '{drug_name_for_check}'")
            except Exception as e:
                logger.error(f"[DOCTOR MED] Allergy pre-check error (continuing): {e}")
                allergy_safety_note = "ALLERGY CHECK: Could not verify allergies. Proceed with caution.\n\n"
        
        # 3a. APPROVED DRUG DIRECT DOSE CALCULATION
        # If the drug is in the approved drugs JSON, calculate dose directly
        # without going through RxNorm/FDA/MCP — the JSON has everything needed.
        if is_dose_query and drug_name_for_check and patient_id:
            approved, drug_data = is_drug_approved(drug_name_for_check)
            if approved and drug_data:
                logger.info(f"[DOCTOR MED] Approved drug '{drug_name_for_check}' — direct dose calculation")
                self._ensure_patient_data(patient_id, context_data)
                patient_name = self._get_patient_name(context_data)
                
                # Extract patient weight from vitals
                weight_kg = None
                if context_data.get("patient_data"):
                    patient_data = context_data["patient_data"]
                    if patient_data.get("vitals") and patient_data["vitals"].get("data"):
                        for vital in patient_data["vitals"]["data"]:
                            vital_name = vital.get('vital_name', '').lower()
                            if 'weight' in vital_name:
                                weight_kg = vital.get('value_numeric')
                                if weight_kg:
                                    break
                
                if weight_kg:
                    weight_kg = float(weight_kg)
                    dose_info = drug_data.get('dose', {})
                    child_dose = dose_info.get('infant_child', {})
                    
                    # Get dose_per_kg — may be a single value or a range
                    dose_per_kg = child_dose.get('mg_per_kg')
                    if dose_per_kg is None:
                        mg_range = child_dose.get('mg_per_kg_range')
                        if mg_range and isinstance(mg_range, list) and len(mg_range) >= 2:
                            dose_per_kg = mg_range[1]  # Use upper end of range
                    
                    if dose_per_kg is not None:
                        dose_per_kg = float(dose_per_kg)
                        calculated_dose = round(weight_kg * dose_per_kg, 1)
                        
                        # Cap at max single dose if specified
                        max_single = child_dose.get('max_single_dose_mg')
                        final_dose = calculated_dose
                        if max_single and calculated_dose > float(max_single):
                            final_dose = float(max_single)
                        
                        # Frequency
                        freq_range = child_dose.get('frequency_hours_range')
                        freq_per_day = child_dose.get('frequency_per_day_range') or child_dose.get('frequency_per_day')
                        if freq_range:
                            frequency = f"Every {freq_range[0]}-{freq_range[1]} hours"
                        elif isinstance(freq_per_day, list):
                            frequency = f"{freq_per_day[0]}-{freq_per_day[1]} times per day"
                        elif freq_per_day:
                            frequency = f"{freq_per_day} times per day"
                        else:
                            frequency = "As directed"
                        
                        max_daily = child_dose.get('max_daily_mg') or child_dose.get('max_daily_mg_per_kg')
                        max_daily_str = ""
                        if child_dose.get('max_daily_mg'):
                            max_daily_str = f"{child_dose['max_daily_mg']} mg"
                        elif child_dose.get('max_daily_mg_per_kg'):
                            max_daily_str = f"{child_dose['max_daily_mg_per_kg']} mg/kg/day ({round(weight_kg * float(child_dose['max_daily_mg_per_kg']), 1)} mg)"
                        
                        response = (
                            f"{allergy_safety_note}"
                            f"**Dose Calculation for {drug_name_for_check.title()} — {patient_name or patient_id}**\n\n"
                            f"- **Patient weight:** {weight_kg} kg\n"
                            f"- **Dose per kg:** {dose_per_kg} mg/kg\n"
                            f"- **Calculated dose:** {weight_kg} × {dose_per_kg} = {calculated_dose} mg\n"
                            f"- **Recommended dose:** {final_dose} mg"
                        )
                        if max_single and calculated_dose > float(max_single):
                            response += f" (capped at max single dose {max_single} mg)"
                        response += f"\n- **Frequency:** {frequency}\n"
                        if max_daily_str:
                            response += f"- **Maximum daily dose:** {max_daily_str}\n"
                        
                        response += (
                            f"\n**Source:** WHO Analgesics/Antipyretics/NSAIDs Approved List\n"
                            f"**Note:** Always verify against current clinical guidelines and patient-specific factors."
                        )
                        
                        logger.info(f"[DOCTOR MED] Direct dose calculation: {drug_name_for_check} {final_dose}mg for {weight_kg}kg")
                        return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                                ["WHO Analgesics/Antipyretics/NSAIDs Approved List", "Patient Vitals"],
                                                patient_id)
                    else:
                        logger.warning(f"[DOCTOR MED] No dose_per_kg found in approved drug data for {drug_name_for_check}")
                else:
                    logger.warning(f"[DOCTOR MED] No weight found for patient {patient_id}, cannot calculate dose directly")

        if drug_intent and patient_id:
            logger.info("[DOCTOR MED] Drug dosage query - activating strict 9-step handler")
            try:
                drug_response = handle_drug_dosage_query(
                    query=user_question,
                    patient_id=patient_id,
                    db_connection=self.sql_agent.db,
                    patient_data=context_data.get("patient_data")
                )
                if drug_response and isinstance(drug_response, str):
                    logger.info("[DOCTOR MED] Drug dosage handler completed - returning formatted response")
                    return self._build_result(user_type, "MEDICATION_QUERY", user_question,
                                            allergy_safety_note + drug_response,
                                            ["Allergy Check", "WHO Analgesics/Antipyretics/NSAIDs Approved List", "DoseCalculator"],
                                            patient_id)
            except Exception as e:
                logger.error(f"[DOCTOR MED] Drug dosage handler error (continuing to MCP): {e}")
        
        # 3. MCP medication search fallback
        try:
            med_results = self.mcp_agent.search_medication(user_question)
            if med_results and med_results.get('count', 0) > 0:
                context_data["mcp_data"]["medications"] = med_results
                context_data["sources"].append("Medication Database (Enhanced)")
                
                # Calculate dose if we have patient data
                if context_data.get("patient_data"):
                    try:
                        patient_data = context_data["patient_data"]
                        weight_kg = None
                        if patient_data.get("vitals") and patient_data["vitals"].get("data"):
                            for vital in patient_data["vitals"]["data"]:
                                vital_name = vital.get('vital_name', '').lower()
                                if 'weight' in vital_name:
                                    weight_kg = vital.get('value_numeric')
                                    if weight_kg:
                                        break
                        age_years = None
                        if patient_data.get("patient") and patient_data["patient"].get("data"):
                            p = patient_data["patient"]["data"][0]
                            birthdate = p.get('birthdate')
                            if birthdate:
                                age_years = self.response_agent.calculate_age_from_birthdate(birthdate)
                        if weight_kg and age_years is not None:
                            med_name = med_results["results"][0].get("name") if med_results.get("results") else None
                            if med_name:
                                dose_result = self.mcp_agent.calculate_medication_dose(
                                    drug_name=med_name,
                                    weight_kg=float(weight_kg),
                                    age_years=float(age_years)
                                )
                                if dose_result and "error" not in dose_result:
                                    med_results["dose_calculation"] = dose_result
                                    logger.info(f"Dose calculated for {med_name}: {dose_result}")
                                    context_data["sources"].append("Patient Vitals (Weight) + FDA/RxNorm")
                    except Exception as e:
                        logger.debug(f"Dose calculation optional - skipped: {e}")
                
                logger.info(f"Medication data retrieved: {med_results['count']} results")
        except Exception as e:
            logger.error(f"Error searching medications: {e}")
        
        # Fall through: return None so pipeline delegates to KB+LLM via shared handler
        return None

    # ====================================================================
    # PATIENT MEDICATION HANDLER
    # ====================================================================
    def _patient_medication_handler(self, user_question, patient_id, context_data, user_type):
        """Patient-specific medication processing.
        
        CHANGE 6: Patient Dose Calculation Hard Block - blocks dosage queries.
        Safety-first: blocks dosage queries with redirect to healthcare provider.
        Only shows active medications list (no dose calculations).
        """
        logger.info("[PATIENT MED] Patient medication query handler activated")
        
        # CHANGE 6: SAFETY BLOCK - Hard block on 16 dose-calculation keywords (patient role only)
        # Filter Keywords — Exact List from user specification
        dose_keywords_exact = [
            "mg/kg",
            "milligram per kg",
            "dose calculation",
            "calculate the dose",
            "calculate dose",
            "how many mg",
            "how much mg",
            "what dose",
            "what is the dose",
            "dosage for",
            "dose for",
            "safe dose",
            "correct dose",
            "how many milligrams",
            "per kilogram"
        ]
        
        query_lower = user_question.lower()
        keyword_found = None
        for keyword in dose_keywords_exact:
            if keyword in query_lower:
                keyword_found = keyword
                break
        
        if keyword_found and user_type.upper() == "PATIENT":
            logger.info(f"[CHANGE 6 SAFETY BLOCK] Patient dose query blocked - keyword: '{keyword_found}'")
            # Return this exact fixed message as specified
            fixed_response = (
                "The dose for your child has been prescribed by your doctor. Please follow the "
                "prescription label or contact your pharmacist directly for any dosing questions."
            )
            return self._build_result(user_type, "MEDICATION_QUERY", user_question, fixed_response,
                                    ["Safety Guidelines"], patient_id)
        
        # If doctor role, proceed normally (not blocked)
        if keyword_found and user_type.upper() == "DOCTOR":
            logger.info(f"[CHANGE 6] Doctor query with keyword '{keyword_found}' - proceeding normally")
        
        # 1.5. PRESCRIBE/SAFETY QUERY — allergy check ONLY (no dose calculation)
        # Handle "can my child take...", "is it safe...", "can I give..." for patients
        prescribe_keywords = ['take', 'safe', 'give', 'administer', 'can ', 'should ', 'ok to']
        is_prescribe_query = any(kw in query_lower for kw in prescribe_keywords)
        
        drug_name_for_check = extract_drug_name(user_question)
        if is_prescribe_query and not keyword_found and drug_name_for_check and patient_id:
            logger.info(f"[PATIENT MED] Prescribe/safety query — running allergy check only for '{drug_name_for_check}'")
            try:
                allergy_fetcher = AllergyOpenMRSFetcher()
                allergy_check = allergy_fetcher.check_drug_allergy(patient_id, drug_name_for_check)
                allergy_fetcher.disconnect()
                
                self._ensure_patient_data(patient_id, context_data)
                patient_name = self._get_patient_name(context_data)
                response = AllergyResponsePatient.format_drug_allergy_check(
                    drug_name_for_check, allergy_check, patient_id, patient_name
                )
                return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                        ["Allergy Check + OpenMRS Records"], patient_id)
            except Exception as e:
                logger.error(f"[PATIENT MED] Allergy check error: {e}")
        
        # 2. Drug information query (indications, contraindications, side effects, warnings, etc.)
        query_lower = user_question.lower()
        drug_info_keywords = ['indication', 'contraindication', 'warning', 'precaution',
                             'adverse effect', 'side effect', 'drug interaction',
                             'properties', 'information about']
        is_drug_info_query = any(kw in query_lower for kw in drug_info_keywords)
        
        if is_drug_info_query:
            drug_name = extract_drug_name(user_question)
            if drug_name:
                logger.info(f"[PATIENT MED] Drug info query for '{drug_name}' - fetching from KB + FDA API")
                try:
                    info_response = extract_drug_information(user_question, drug_name)
                    if info_response:
                        response = (
                            f"**Drug Information: {drug_name.title()}**\n\n"
                            f"{info_response}\n\n"
                            "**Note:** This is general drug information. Your child's specific risks "
                            "depend on their age, weight, and health.\n\n"
                            "**Always consult your doctor before giving any medication to your child.**"
                        )
                        return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                                ["Drug Knowledge Base", "FDA OpenFDA API"], patient_id)
                except Exception as e:
                    logger.error(f"[PATIENT MED] Error fetching drug information: {e}")

        # 3. Active medications query
        active_med_keywords = ['active', 'current', 'taking', 'prescribed', 'using', 'on', 'receives', 'getting', 'medications', 'medicine']
        is_active_med_query = any(kw in user_question.lower() for kw in active_med_keywords)
        
        if is_active_med_query and patient_id:
            logger.info(f"[PATIENT MED] Active medications query for patient {patient_id}")
            try:
                med_fetcher = MedicationOpenMRSFetcher()
                active_medications = med_fetcher.get_active_medications(patient_id)
                med_fetcher.disconnect()
                
                if active_medications:
                    self._ensure_patient_data(patient_id, context_data)
                    patient_name = self._get_patient_name(context_data)
                    response = MedicationResponsePatient.format_active_medications(
                        active_medications, patient_name
                    )
                    return self._build_result(user_type, "MEDICATION_QUERY", user_question, response,
                                            ["Active Medications + OpenMRS Records"], patient_id)
                else:
                    logger.info(f"[PATIENT MED] No active medications found for patient {patient_id}")
                    return self._build_result(user_type, "MEDICATION_QUERY", user_question,
                                            f"Patient {patient_id} currently has no active medications.",
                                            ["OpenMRS Records"], patient_id)
            except Exception as e:
                logger.error(f"[PATIENT MED] Error fetching active medications: {e}")
        
        # Fall through: return None so pipeline delegates to KB+LLM via shared handler
        return None

    # ====================================================================
    # DRUG INFORMATION HANDLERS
    # ====================================================================
    def _doctor_drug_information_handler(self, user_question, user_type):
        """Doctor-specific drug information processing.
        
        Fetches comprehensive drug information including side effects,
        contraindications, warnings, and interactions from FDA/RxNorm.
        Provides targeted response showing only what was asked for.
        """
        logger.info("[DOCTOR DRUG INFO] Doctor drug information handler activated")
        
        try:
            drug_name = extract_drug_name(user_question)
            
            if not drug_name:
                logger.warning("[DOCTOR DRUG INFO] No drug name extracted from question")
                return None
            
            logger.info(f"[DOCTOR DRUG INFO] Fetching drug information for '{drug_name}'")
            
            response = self.response_agent.generate_drug_information_response(
                drug_name, 
                user_type="DOCTOR",
                original_question=user_question  # Pass original question for targeted response
            )
            
            if response:
                return self._build_result(user_type, "DRUG_INFORMATION_QUERY", user_question, response,
                                        ["FDA OpenFDA API", "RxNorm API"], None)
            else:
                logger.warning(f"[DOCTOR DRUG INFO] No drug information found for '{drug_name}'")
                return None
        
        except Exception as e:
            logger.error(f"[DOCTOR DRUG INFO] Error fetching drug information: {e}", exc_info=True)
            return None

    def _patient_drug_information_handler(self, user_question, user_type):
        """Patient-specific drug information processing.
        
        Fetches drug information formatted for patient understanding,
        with simplified language and practical guidance.
        Provides targeted response showing only what was asked for.
        """
        logger.info("[PATIENT DRUG INFO] Patient drug information handler activated")
        
        try:
            drug_name = extract_drug_name(user_question)
            
            if not drug_name:
                logger.warning("[PATIENT DRUG INFO] No drug name extracted from question")
                return None
            
            logger.info(f"[PATIENT DRUG INFO] Fetching drug information for '{drug_name}'")
            
            response = self.response_agent.generate_drug_information_response(
                drug_name, 
                user_type="PATIENT",
                original_question=user_question  # Pass original question for targeted response
            )
            
            if response:
                return self._build_result(user_type, "DRUG_INFORMATION_QUERY", user_question, response,
                                        ["FDA OpenFDA API", "RxNorm API"], None)
            else:
                logger.warning(f"[PATIENT DRUG INFO] No drug information found for '{drug_name}'")
                return None
        
        except Exception as e:
            logger.error(f"[PATIENT DRUG INFO] Error fetching drug information: {e}", exc_info=True)
            return None

    # ====================================================================
    # HELPER METHODS
    # ====================================================================
    def _build_result(self, user_type, intent, user_question, response, sources, patient_id, **extra):
        """Build a standardized result dictionary and save it"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "user_type": user_type,
            "intent": intent,
            "question": user_question,
            "response": response,
            "sources": sources,
            "patient_id": patient_id
        }
        result.update(extra)
        self.save_response(result)
        return result

    def _get_patient_name(self, context_data):
        """Extract patient name from context data"""
        if context_data.get("patient_data"):
            patient_info = context_data["patient_data"].get("patient", {}).get("data", [])
            if patient_info:
                return patient_info[0].get("given_name")
        return None

    def _out_of_scope_response(self, user_question, intent, patient_id, user_type, role="patient"):
        """Short decline for questions outside the pipeline's scope"""
        if role == "doctor":
            response = (
                "I'm sorry, that question is outside my scope. "
                "I can only assist with patient clinical data, medications, allergies, "
                "immunizations, vitals, and milestones."
            )
        else:
            response = (
                "I'm sorry, I cannot help with that. "
                "Please ask your doctor or healthcare provider."
            )
        return self._build_result(user_type, intent, user_question, response,
                                 ["Scope Policy"], patient_id)

    def _ensure_patient_data(self, patient_id, context_data):
        """Ensure patient data is loaded into context_data, fetch if needed"""
        if context_data.get("patient_data"):
            return True
        if not patient_id:
            return False
        try:
            validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
            if validation_status is True:
                patient_data = self.sql_agent.query_patient_record(patient_id)
                context_data["patient_data"] = patient_data
                context_data["sources"] = ["Patient Record (OpenMRS)"]
                logger.info(f"Patient data loaded for ID: {patient_id}")
                return True
        except Exception as e:
            logger.debug(f"Could not retrieve patient data: {e}")
        return False

    # ====================================================================
    # SHARED INTENT HANDLER (all intents except MEDICATION_QUERY)
    # ====================================================================
    def _handle_shared_intents(self, user_question, intent, patient_id, context_data, user_type):
        """Handle all intents shared between doctor and patient pipelines.
        
        Each intent handler already has internal role-based formatting (if doctor/else patient).
        KB + LLM response only runs for intents that need it (MILESTONE, PATIENT_RECORD, GENERAL).
        """
        # Query past medications if PAST_MEDICATIONS_QUERY intent
        # ====================================================================
        # PAST MEDICATIONS: "What medications was my child on before?"
        # Retrieves discontinued/stopped medications from OpenMRS
        # ====================================================================
        if intent == "PAST_MEDICATIONS_QUERY":
            logger.info(f"[PAST MEDICATIONS] Past medications query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    # Fetch past/discontinued medications directly from OpenMRS
                    med_fetcher = MedicationOpenMRSFetcher()
                    past_medications = med_fetcher.get_past_medications(patient_id)
                    med_fetcher.disconnect()
                    
                    if past_medications:
                        # Get patient name if available
                        patient_name = None
                        if not context_data.get("patient_data"):
                            validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                            if validation_status is True:
                                try:
                                    patient_data = self.sql_agent.query_patient_record(patient_id)
                                    context_data["patient_data"] = patient_data
                                except Exception as e:
                                    logger.debug(f"Could not retrieve patient data: {e}")
                        
                        if context_data.get("patient_data"):
                            patient_info = context_data.get("patient_data", {}).get("patient", {}).get("data", [])
                            if patient_info:
                                patient_name = patient_info[0].get("given_name")
                        
                        # Format and return past medications
                        if user_type == "DOCTOR":
                            # Doctor gets detailed clinical information
                            response = "**PAST MEDICATIONS (DISCONTINUED)**\n\n"
                            response += f"Patient: {patient_name or patient_id}\n"
                            response += "-" * 70 + "\n\n"
                            
                            for med in past_medications:
                                response += f"• **{med['drug_name']}**\n"
                                response += f"  - Status: {med['status']}\n"
                                if med.get('indication'):
                                    response += f"  - Indication: {med['indication']}\n"
                                if med['dose']:
                                    response += f"  - Dose: {med['dose']} {med['dose_units'] or 'unit(s)'}\n"
                                if med['frequency']:
                                    response += f"  - Frequency: {med['frequency']}\n"
                                if med['route']:
                                    response += f"  - Route: {med['route']}\n"
                                if med['date_activated']:
                                    response += f"  - Started: {med['date_activated'][:10]}\n"
                                if med['date_stopped']:
                                    response += f"  - Stopped: {med['date_stopped'][:10]}\n"
                                if med['instructions']:
                                    response += f"  - Instructions: {med['instructions']}\n"
                                response += "\n"
                        else:
                            # Patient gets simple summary
                            response = f"**Your Child's Past Medications**\n\n"
                            response += "The following medications were given in the past but are no longer being used:\n\n"
                            
                            for med in past_medications:
                                response += f"• **{med['drug_name']}**\n"
                                if med.get('indication'):
                                    response += f"  Used for: {med['indication']}\n"
                                if med['date_stopped']:
                                    response += f"  Stopped: {med['date_stopped'][:10]}\n"
                                response += "\n"
                            
                            response += "If you need more details about any of these medications or why they were discontinued, "
                            response += "please contact your doctor or pharmacist."
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "PAST_MEDICATIONS_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["Past Medications + OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        logger.info(f"[PAST MEDICATIONS] Past medications returned - {len(past_medications)} medications found")
                        return result
                    else:
                        logger.info(f"[PAST MEDICATIONS] No past medications found for patient {patient_id}")
                        response = f"Patient {patient_id} has no record of discontinued medications."
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "PAST_MEDICATIONS_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        return result
                except Exception as e:
                    logger.error(f"[PAST MEDICATIONS] Error fetching past medications: {e}")
                    response = "Sorry, I encountered an error retrieving past medication history. Please try again."
                    result = {
                        "timestamp": datetime.now().isoformat(),
                        "user_type": user_type,
                        "intent": "PAST_MEDICATIONS_QUERY",
                        "question": user_question,
                        "response": response,
                        "sources": ["Error Log"],
                        "patient_id": patient_id
                    }
                    self.save_response(result)
                    return result

        # Query allergies if ALLERGY_QUERY intent
        if intent == "ALLERGY_QUERY":
            logger.info(f"[ALLERGIES] Allergy query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    allergy_fetcher = AllergyOpenMRSFetcher()
                    
                    # Extract drug name from question if asking about specific drug
                    drug_name = None
                    question_lower = user_question.lower()
                    
                    # First try the robust regex-based extractor (handles "prescribe X", "give X", etc.)
                    drug_name = extract_drug_name(user_question)
                    
                    # Fallback: try hardcoded variations for typo correction (e.g., "pencillin" → "penicillin")
                    if not drug_name:
                        drug_variations = {
                            'penicillin': ['pencillin', 'penicilan', 'penicilin'],
                            'amoxicillin': ['amoxcilin', 'amoxicilin'],
                            'sulfamethoxazole': ['sulfametoxazole', 'sulfa', 'sulfamethoxazol'],
                        }
                        
                        for canonical_name, variations in drug_variations.items():
                            for variation in variations:
                                if variation in question_lower:
                                    drug_name = canonical_name
                                    break
                            if drug_name:
                                break
                    
                    # Get patient name
                    patient_name = None
                    if not context_data.get("patient_data"):
                        validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                        if validation_status is True:
                            try:
                                patient_data = self.sql_agent.query_patient_record(patient_id)
                                context_data["patient_data"] = patient_data
                            except Exception as e:
                                logger.debug(f"Could not retrieve patient data: {e}")
                    
                    if context_data.get("patient_data"):
                        patient_info = context_data.get("patient_data", {}).get("patient", {}).get("data", [])
                        if patient_info:
                            patient_name = patient_info[0].get("given_name")
                    
                    # Extract food/substance name for safety queries like "can I give egg to my child"
                    food_substances = {
                        'egg': ['egg', 'eggs'],
                        'milk': ['milk', 'dairy', 'lactose'],
                        'peanut': ['peanut', 'peanuts'],
                        'wheat': ['wheat', 'gluten'],
                        'soy': ['soy', 'soya', 'soybean'],
                        'shellfish': ['shellfish', 'shrimp', 'crab', 'lobster'],
                        'fish': ['fish', 'cod', 'salmon', 'tuna'],
                        'corn': ['corn', 'maize'],
                        'nut': ['nut', 'nuts', 'almond', 'cashew', 'walnut'],
                        'dust': ['dust'],
                        'gelatin': ['gelatin', 'jelly'],
                        'latex': ['latex'],
                    }
                    substance_name = None
                    for canonical, variations in food_substances.items():
                        for v in variations:
                            if v in question_lower:
                                substance_name = canonical
                                break
                        if substance_name:
                            break
                    
                    # If a food/substance is mentioned (but NOT a drug), do substance allergy check
                    if substance_name and not drug_name:
                        logger.info(f"[ALLERGIES] Substance safety check for '{substance_name}'")
                        substance_check = allergy_fetcher.check_substance_allergy(patient_id, substance_name)
                        
                        if substance_check.get('is_allergic'):
                            response = (
                                f"{'='*70}\n"
                                f"[WARNING] ALLERGY ALERT - {substance_name.upper()}\n"
                                f"{'='*70}\n\n"
                                f"Patient" + (f" {patient_name}" if patient_name else "") + " has a documented allergy:\n\n"
                                f"  Allergen: {substance_check['allergen_matched']}\n"
                                f"  Type: {substance_check['allergen_type']}\n"
                                f"  Severity: {substance_check['severity']}\n\n"
                                f"{substance_check['message']}\n\n"
                                f"{'='*70}\n"
                            )
                            if user_type.lower() == "patient":
                                response += (
                                    "Do NOT give this to your child.\n"
                                    "If accidentally consumed, watch for:\n"
                                    "  - Rash, hives, or swelling\n"
                                    "  - Difficulty breathing\n"
                                    "  - Stomach pain, vomiting, or diarrhea\n\n"
                                    "Seek medical help immediately if any symptoms appear.\n\n"
                                    "Source: Patient Medical Records\n"
                                )
                            else:
                                response += (
                                    "Clinical Recommendation:\n"
                                    "  - Do not administer this substance\n"
                                    "  - Consider allergy testing to confirm severity\n"
                                    "  - Document avoidance in dietary plan\n"
                                    "  - Review medications for excipients derived from this substance\n\n"
                                    "Source: OpenMRS Patient Allergy Record\n"
                                )
                        else:
                            response = (
                                f"{'='*70}\n"
                                f"[OK] {substance_name.upper()} - ALLERGY CHECK\n"
                                f"{'='*70}\n\n"
                                f"{substance_check['message']}\n\n"
                            )
                            if user_type.lower() == "patient":
                                response += (
                                    "Based on medical records, no allergy to this substance is documented.\n"
                                    "However, always introduce new foods carefully and watch for any reactions.\n"
                                    "If you notice any allergic symptoms, consult your doctor immediately.\n\n"
                                    "Source: Patient Medical Records\n"
                                )
                            else:
                                response += (
                                    "No documented allergy. Standard precautions apply.\n\n"
                                    "Source: OpenMRS Patient Allergy Record\n"
                                )
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "ALLERGY_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["AllergiesOpenMRS Records"],
                            "patient_id": patient_id,
                        }
                        allergy_fetcher.disconnect()
                        self.save_response(result)
                        logger.info(f"[ALLERGIES] Substance allergy check completed for '{substance_name}'")
                        return result
                    
                    # If asking about specific drug, check contraindication
                    if drug_name:
                        logger.info(f"[ALLERGIES] Checking drug contraindication for {drug_name}")
                        allergy_check = allergy_fetcher.check_drug_allergy(patient_id, drug_name)
                        
                        # Check if this is a hybrid question (also asking about dosage)
                        dosage_keywords = ['how much', 'how many', 'what dose', 'what dosage', 'give how much', 'can i give']
                        is_hybrid_question = any(kw in user_question.lower() for kw in dosage_keywords)
                        
                        # Use patient-friendly formatter if user is patient, clinical if doctor
                        if user_type.lower() == "patient":
                            response = AllergyResponsePatient.format_drug_allergy_check(
                                drug_name,
                                allergy_check,
                                patient_id,
                                patient_name
                            )
                            
                            # Add brief dosage note if this is a hybrid question (avoid duplication)
                            if is_hybrid_question:
                                dosage_note = (
                                    "\n\n**DOSAGE NOTE:** For the correct dosage, please consult your doctor or pharmacist. They will determine the proper amount based on your child's age, weight, and medical condition."
                                )
                                response += dosage_note
                        else:
                            response = AllergyResponseDoctor.format_drug_allergy_check(
                                drug_name,
                                allergy_check,
                                patient_id,
                                patient_name
                            )
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "ALLERGY_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["AllergiesOpenMRS Records"],
                            "patient_id": patient_id,
                            "is_hybrid_question": is_hybrid_question
                        }
                        allergy_fetcher.disconnect()
                        self.save_response(result)
                        logger.info(f"[ALLERGIES] Allergy check completed - Hybrid: {is_hybrid_question}")
                        return result
                    else:
                        # General allergy profile requested
                        logger.info(f"[ALLERGIES] Retrieving complete allergy profile for patient {patient_id}")
                        allergies = allergy_fetcher.get_patient_allergies(patient_id)
                        
                        # Use patient-friendly formatter if user is patient, clinical if doctor
                        if user_type.lower() == "patient":
                            # Detect what specific allergy type the patient is asking about
                            allergy_type, match_count = AllergyResponsePatient.detect_allergy_type_from_question(user_question)
                            
                            # Detect if patient is asking about self or about a child/dependent
                            asking_about_self = AllergyResponsePatient.detect_asking_about_self(user_question)
                            
                            if allergy_type in ['FOOD', 'DRUG', 'ENVIRONMENT']:
                                # Patient asking about specific allergy type
                                logger.info(f"[ALLERGIES] Patient asking specifically about {allergy_type} allergies - filtering results (matched {match_count} keywords)")
                                response = AllergyResponsePatient.format_allergy_by_type(
                                    allergy_type,
                                    allergies,
                                    patient_id,
                                    patient_name,
                                    asking_about_self=asking_about_self
                                )
                            else:
                                # Patient asking about allergies in general
                                logger.info("[ALLERGIES] Patient asking about allergies in general - showing all allergies")
                                response = AllergyResponsePatient.format_patient_allergies(
                                    allergies,
                                    patient_id,
                                    patient_name
                                )
                        else:
                            # Doctor view - also detect specific allergy type being asked about
                            allergy_type, match_count = AllergyResponsePatient.detect_allergy_type_from_question(user_question)
                            
                            if allergy_type in ['FOOD', 'DRUG', 'ENVIRONMENT']:
                                # Doctor asking about specific allergy type
                                logger.info(f"[ALLERGIES] Doctor asking specifically about {allergy_type} allergies - filtering results (matched {match_count} keywords)")
                                response = AllergyResponseDoctor.format_allergy_by_type(
                                    allergy_type,
                                    allergies,
                                    patient_id,
                                    patient_name
                                )
                            else:
                                # Doctor asking about allergies in general - show all
                                logger.info("[ALLERGIES] Doctor asking about allergies in general - showing all allergies")
                                response = AllergyResponseDoctor.format_patient_allergies(
                                    allergies,
                                    patient_id,
                                    patient_name
                                )
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "ALLERGY_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["Allergies + OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        allergy_fetcher.disconnect()
                        self.save_response(result)
                        logger.info(f"[ALLERGIES] Allergy profile returned")
                        return result
                        
                except Exception as e:
                    logger.error(f"[ALLERGIES] Error processing allergy query: {e}")
                    # Fall through to general response

        # ====================================================================
        # MEDICATION_INFO_QUERY: "What medicine has been prescribed for my child?"
        # ====================================================================
        if intent == "MEDICATION_INFO_QUERY":
            logger.info(f"[MED_INFO] Medication information query detected")
            
            if patient_id:
                try:
                    med_fetcher = MedicationOpenMRSFetcher()
                    active_medications = med_fetcher.get_active_medications(patient_id)
                    med_fetcher.disconnect()
                    
                    # Get patient name if not already retrieved
                    patient_name = None
                    if not context_data.get("patient_data"):
                        validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                        if validation_status is True:
                            try:
                                patient_data = self.sql_agent.query_patient_record(patient_id)
                                context_data["patient_data"] = patient_data
                            except Exception as e:
                                logger.debug(f"Could not retrieve patient data: {e}")
                    
                    if context_data.get("patient_data"):
                        patient_info = context_data.get("patient_data", {}).get("patient", {}).get("data", [])
                        if patient_info:
                            patient_name = patient_info[0].get("given_name")
                    
                    if active_medications:
                        # Format medication list for patient (WITH dosage for active meds since they need to know what's prescribed)
                        if user_type.lower() == "patient":
                            response = (
                                f"**Your Current Medications for {patient_name or 'your child'}:**\n\n"
                            )
                            for idx, med in enumerate(active_medications, 1):
                                med_name = med.get('drug_name', 'Unknown')
                                dose = med.get('dose', 'As prescribed')
                                dose_units = med.get('dose_units', '')
                                route = med.get('route', 'oral').title() if med.get('route') else 'Oral'
                                frequency = med.get('frequency', 'As prescribed')
                                indication = med.get('indication', 'Not specified')
                                
                                # Convert frequency codes to readable format
                                frequency_readable = frequency
                                if frequency and str(frequency).replace('.', '', 1).isdigit():
                                    freq_map = {
                                        '1': 'Once daily',
                                        '2': 'Twice daily',
                                        '3': 'Three times daily',
                                        '4': 'Four times daily',
                                        '0.5': 'Every other day',
                                        '7': 'Once weekly'
                                    }
                                    frequency_readable = freq_map.get(str(frequency), f'{frequency} times daily')
                                
                                response += f"{idx}. **{med_name}**\n"
                                response += f"   - Indication: {indication}\n"
                                response += f"   - Dose: {dose}"
                                if dose_units:
                                    response += f" {dose_units}"
                                response += "\n"
                                response += f"   - Frequency: {frequency_readable}\n"
                                response += f"   - Form: {route}\n\n"
                            
                            response += (
                                "**Important:**\n"
                                "- Take these medications exactly as your doctor prescribed\n"
                                "- Do not stop taking them without your doctor's approval\n"
                                "- Report any side effects to your healthcare provider\n"
                                "- If you have questions about these medications, consult your healthcare provider\n"
                            )
                        else:
                            # Doctor view - include full details including indication
                            response = (
                                f"**Active Medications - Patient {patient_name or patient_id}:**\n\n"
                            )
                            for idx, med in enumerate(active_medications, 1):
                                med_name = med.get('drug_name', 'Unknown')
                                dose = med.get('dose', 'N/A')
                                dose_units = med.get('dose_units', '')
                                frequency = med.get('frequency', 'As prescribed')
                                instructions = med.get('instructions', 'None')
                                route = med.get('route', 'oral').title() if med.get('route') else 'Oral'
                                date_activated = med.get('date_activated', 'Unknown date')
                                indication = med.get('indication', 'Not specified')
                                
                                response += f"{idx}. **{med_name}**\n"
                                response += f"   - Indication: {indication}\n"
                                response += f"   - Dose: {dose}"
                                if dose_units:
                                    response += f" {dose_units}"
                                response += "\n"
                                response += f"   - Frequency: {frequency}\n"
                                response += f"   - Route: {route}\n"
                                response += f"   - Instructions: {instructions}\n"
                                response += f"   - Started: {date_activated}\n\n"
                            
                            response += "Clinical Notes:\n"
                            response += "- Verify dosing is appropriate for patient age/weight\n"
                            response += "- Check for drug interactions\n"
                            response += "- Monitor patient compliance\n"
                            response += "- Review indications and consider deprescribing if no longer indicated\n"
                    else:
                        response = f"No active medications are currently recorded for patient {patient_id}."
                    
                    result = {
                        "timestamp": datetime.now().isoformat(),
                        "user_type": user_type,
                        "intent": "MEDICATION_INFO_QUERY",
                        "question": user_question,
                        "response": response,
                        "sources": ["Active Medications + OpenMRS Records"],
                        "patient_id": patient_id
                    }
                    self.save_response(result)
                    logger.info(f"[MED_INFO] Active medications information returned")
                    return result
                    
                except Exception as e:
                    logger.error(f"[MED_INFO] Error retrieving medication info: {e}")

        # ====================================================================
        # MEDICATION_EMERGENCY: "Overdose, missed dose, emergency"
        # ====================================================================
        if intent == "MEDICATION_EMERGENCY":
            logger.info(f"[MED_EMERGENCY] MEDICATION EMERGENCY DETECTED - SAFETY PRIORITY")
            
            # Detect specific emergency type
            question_lower = user_question.lower()
            emergency_type = "UNKNOWN"
            
            if any(kw in question_lower for kw in ['overdose', 'too much', 'accidentally took', 'double dose', 'two doses']):
                emergency_type = "OVERDOSE"
            elif any(kw in question_lower for kw in ['missed', 'forgot', 'did not give']):
                emergency_type = "MISSED_DOSE"
            elif any(kw in question_lower for kw in ['poison', 'toxic', 'toxin']):
                emergency_type = "POISONING"
            
            logger.warning(f"[MED_EMERGENCY] Emergency type: {emergency_type}")
            
            # Always redirect patient emergencies to medical professionals
            if user_type.lower() == "patient":
                response = (
                    f"**⚠️ MEDICAL EMERGENCY - {emergency_type}**\n\n"
                    "This is a potentially serious situation that requires immediate professional help.\n\n"
                    "**PLEASE DO ONE OF THE FOLLOWING IMMEDIATELY:**\n"
                    "1. **Call Emergency Services (Ambulance)** - Dial 108 or your local emergency number\n"
                    "2. **Go to the Nearest Emergency Room**\n"
                    "3. **Call Poison Control Center** - If poisoning is suspected\n"
                    "4. **Contact Your Doctor Immediately**\n\n"
                    "**DO NOT rely on this chatbot for emergency medical decisions.**\n\n"
                    "Be prepared to tell medical professionals:\n"
                    f"- The patient's name and age\n"
                    f"- The medication name and strength\n"
                    f"- When it was taken\n"
                    f"- How much was taken\n"
                    f"- Any symptoms experienced\n"
                )
            else:
                # Doctor query - direct action required
                response = (
                    f"⚠️ **MEDICATION EMERGENCY - {emergency_type}**\n\n"
                    "**CALL 911 FOR MEDICAL EMERGENCY**\n\n"
                    "or\n\n"
                    "**REACH OUT TO YOUR PRACTITIONER IMMEDIATELY**\n\n"
                    "This situation requires direct medical intervention and cannot be managed through this system."
                )
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "user_type": user_type,
                "intent": "MEDICATION_EMERGENCY",
                "question": user_question,
                "response": response,
                "sources": ["Emergency Guidelines", "Safety Protocols"],
                "patient_id": patient_id,
                "emergency_flag": True
            }
            self.save_response(result)
            logger.warning(f"[MED_EMERGENCY] Emergency response sent to {user_type}")
            return result

        # ====================================================================
        # MEDICATION_COMPATIBILITY_QUERY: "Can my child take X and Y together?"
        # ====================================================================
        if intent == "MEDICATION_COMPATIBILITY_QUERY":
            logger.info(f"[MED_COMPAT] Drug compatibility/interaction query detected")
            
            # Extract drug names from question
            common_drugs = ['ibuprofen', 'paracetamol', 'acetaminophen', 'aspirin', 'amoxicillin',
                          'cough syrup', 'cold medicine', 'fever medicine', 'pain relief']
            mentioned_drugs = [drug for drug in common_drugs if drug in user_question.lower()]
            
            if user_type.lower() == "patient":
                response = (
                    "**Drug Combination Safety Check**\n\n"
                    "Taking multiple medications together can sometimes cause interactions.\n\n"
                    "**IMPORTANT: ALWAYS consult your doctor or pharmacist before giving your child**\n"
                    "**any combination of medications.**\n\n"
                    "Your healthcare provider will consider:\n"
                    "- Your child's age and weight\n"
                    "- Your child's medical conditions\n"
                    "- All medications and supplements your child is taking\n"
                    "- Potential interactions between drugs\n\n"
                    "**Do not mix medications without medical guidance.**\n"
                    "Contact your pharmacist or doctor with the specific medications you want to combine."
                )
            else:
                # Doctor query - can provide drug interaction information
                response = (
                    "**Drug Compatibility Assessment**\n\n"
                    "For drug interaction checking, please verify:\n"
                    "1. Patient's age and weight\n"
                    "2. Complete list of current medications\n"
                    "3. Dosages and frequencies of each medication\n"
                    "4. Patient's renal/hepatic function\n\n"
                    "Recommended resources:\n"
                    "- Check FDA drug interactions database\n"
                    "- Verify using Lexi-Interact or similar reference\n"
                    "- Contact pharmacy for contraindication review\n"
                )
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "user_type": user_type,
                "intent": "MEDICATION_COMPATIBILITY_QUERY",
                "question": user_question,
                "response": response,
                "sources": ["Drug Interaction Guidelines"],
                "patient_id": patient_id
            }
            self.save_response(result)
            logger.info(f"[MED_COMPAT] Drug compatibility guidance provided")
            return result

        # ====================================================================
        # MEDICATION_ADMINISTRATION_QUERY: "How to give, with food, vomited, frequency, etc."
        # ====================================================================
        if intent == "MEDICATION_ADMINISTRATION_QUERY":
            logger.info(f"[MED_ADMIN] Medication administration query detected")
            
            # Detect specific administration issue
            question_lower = user_question.lower()
            is_frequency_question = any(kw in question_lower for kw in ['frequency', 'how often', 'times per day', 'times daily', 'dosing frequency', 'interval', 'between doses', 'how many times'])
            
            admin_type = "GENERAL"
            if is_frequency_question:
                admin_type = "FREQUENCY"
            elif any(kw in question_lower for kw in ['crush', 'break', 'powder', 'dissolve']):
                admin_type = "CRUSHING_CRUSHING"
            elif any(kw in question_lower for kw in ['food', 'empty stomach', 'milk']):
                admin_type = "WITH_FOOD"
            elif any(kw in question_lower for kw in ['spit', 'vomit', 'vomited', 'throw up']):
                admin_type = "VOMITED_SPIT"
            elif any(kw in question_lower for kw in ['refused', 'refuses', 'refuse', 'juice', 'mix']):
                admin_type = "REFUSED"
            
            # For frequency questions, retrieve and show active medication frequencies
            if is_frequency_question:
                logger.info(f"[MED_ADMIN] Frequency/dosing question detected")
                
                # Try to extract a specific drug name from the question
                asked_drug_name = extract_drug_name(user_question)
                
                # Look up drug knowledge base for the specific drug's frequency data
                drug_kb_frequency = None
                if asked_drug_name:
                    try:
                        kb_path = os.path.join(os.path.dirname(__file__), 'data', 'drug_knowledge_base.json')
                        with open(kb_path, 'r') as f:
                            drug_kb = json.load(f)
                        drugs_kb = drug_kb.get('drugs', {})
                        for drug_key, drug_info in drugs_kb.items():
                            canonical = drug_info.get('canonical_name', '').lower()
                            aliases = [alias.lower() for alias in drug_info.get('aliases', [])]
                            if asked_drug_name.lower() == drug_key.lower() or asked_drug_name.lower() == canonical or asked_drug_name.lower() in aliases:
                                dosing = drug_info.get('dosing', {})
                                drug_kb_frequency = {
                                    'drug_name': drug_key,
                                    'category': drug_info.get('category', 'Unknown'),
                                    'dosing': dosing,
                                    'indications': drug_info.get('indications', []),
                                    'max_warnings': drug_info.get('major_warnings', [])
                                }
                                logger.info(f"[MED_ADMIN] Found {asked_drug_name} frequency data in drug KB")
                                break
                    except Exception as e:
                        logger.warning(f"[MED_ADMIN] Could not load drug KB for frequency: {e}")
                
                # Also try FDA API if drug KB didn't have data
                fda_frequency = None
                if asked_drug_name and not drug_kb_frequency:
                    try:
                        from utils.fda_api_skill import FDAAPISkill
                        fda_skill = FDAAPISkill()
                        fda_data = fda_skill.get_drug_label(asked_drug_name)
                        if fda_data and fda_data.get('dosage_and_administration'):
                            fda_frequency = fda_data
                            logger.info(f"[MED_ADMIN] Got frequency data from FDA API for {asked_drug_name}")
                    except Exception as e:
                        logger.warning(f"[MED_ADMIN] FDA API lookup failed: {e}")
                
                # Fetch active medications from OpenMRS
                if patient_id:
                    try:
                        med_fetcher = MedicationOpenMRSFetcher()
                        active_medications = med_fetcher.get_active_medications(patient_id)
                        med_fetcher.disconnect()
                        logger.info(f"[MED_ADMIN] Retrieved {len(active_medications)} medications for frequency display")
                    except Exception as e:
                        logger.error(f"[MED_ADMIN] Error fetching medications: {e}")
                        active_medications = []
                else:
                    active_medications = []
                
                # Get patient name from context or retrieve it
                patient_name = None
                if not context_data.get("patient_data") and patient_id:
                    try:
                        validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                        if validation_status is True:
                            patient_data = self.sql_agent.query_patient_record(patient_id)
                            context_data["patient_data"] = patient_data
                    except Exception as e:
                        logger.debug(f"[MED_ADMIN] Could not retrieve patient data: {e}")
                
                if context_data.get("patient_data"):
                    patient_info = context_data.get("patient_data", {}).get("patient", {}).get("data", [])
                    if patient_info:
                        patient_name = patient_info[0].get("given_name")
                
                # Build response: combine drug KB data + active medication data
                response = ""
                
                # Section 1: Drug-specific frequency from KB / FDA
                if drug_kb_frequency:
                    dosing = drug_kb_frequency['dosing']
                    response += f"**Recommended Dosing Frequency for {asked_drug_name.title()}**\n"
                    response += f"Category: {drug_kb_frequency['category']}\n\n"
                    
                    for age_group, dose_info in dosing.items():
                        if isinstance(dose_info, dict):
                            freq_hours = dose_info.get('frequency_hours') or dose_info.get('frequency_hours_range')
                            min_interval = dose_info.get('min_interval_hours')
                            max_daily = dose_info.get('max_daily_dose_mg')
                            notes = dose_info.get('notes', '')
                            
                            response += f"  **{age_group.replace('_', ' ').title()}:**\n"
                            if isinstance(freq_hours, list):
                                response += f"    - Frequency: Every {freq_hours[0]}-{freq_hours[1]} hours\n"
                            elif freq_hours:
                                times_per_day = int(24 / freq_hours) if freq_hours > 0 else 'N/A'
                                response += f"    - Frequency: Every {freq_hours} hours ({times_per_day} times per day)\n"
                            if min_interval:
                                response += f"    - Minimum interval: {min_interval} hours between doses\n"
                            if max_daily:
                                response += f"    - Maximum daily dose: {max_daily} mg\n"
                            if notes:
                                response += f"    - Note: {notes}\n"
                            response += "\n"
                    
                    if drug_kb_frequency.get('max_warnings'):
                        response += "**Important Warnings:**\n"
                        for warning in drug_kb_frequency['max_warnings'][:3]:
                            response += f"  - {warning}\n"
                        response += "\n"
                    
                    response += f"Source: Drug Knowledge Base\n\n"
                
                elif fda_frequency:
                    response += f"**FDA Dosing Information for {asked_drug_name.title()}**\n\n"
                    if fda_frequency.get('dosage_and_administration'):
                        response += f"{fda_frequency['dosage_and_administration']}\n\n"
                    response += f"Source: FDA OpenFDA API\n\n"
                
                # Section 2: Patient's active medications from OpenMRS
                if active_medications:
                    response += "=" * 50 + "\n"
                    if user_type.lower() == "patient":
                        response += f"**Active Medications for {patient_name or 'Your Child'}:**\n\n"
                        for idx, med in enumerate(active_medications, 1):
                            med_name = med.get('drug_name', 'Unknown')
                            frequency = med.get('frequency', 'As prescribed by your doctor')
                            indication = med.get('indication', 'Not specified')
                            
                            frequency_readable = frequency
                            if frequency and str(frequency).replace('.', '', 1).isdigit():
                                freq_map = {
                                    '1': 'Once daily', '2': 'Twice daily',
                                    '3': 'Three times daily', '4': 'Four times daily',
                                    '0.5': 'Every other day', '7': 'Once weekly'
                                }
                                frequency_readable = freq_map.get(str(frequency), f'{frequency} times daily')
                            
                            response += f"{idx}. **{med_name}**\n"
                            response += f"   - Used for: {indication}\n"
                            response += f"   - Frequency: {frequency_readable}\n\n"
                    else:
                        response += f"**Active Medications - Patient {patient_name or patient_id}:**\n\n"
                        for idx, med in enumerate(active_medications, 1):
                            med_name = med.get('drug_name', 'Unknown')
                            dose = med.get('dose', 'N/A')
                            dose_units = med.get('dose_units', '')
                            frequency = med.get('frequency', 'N/A')
                            route = med.get('route', 'oral').title() if med.get('route') else 'Oral'
                            indication = med.get('indication', 'Not specified')
                            
                            response += f"{idx}. **{med_name}**\n"
                            response += f"   - Indication: {indication}\n"
                            response += f"   - Dose: {dose}"
                            if dose_units:
                                response += f" {dose_units}"
                            response += "\n"
                            response += f"   - Frequency: {frequency}\n"
                            response += f"   - Route: {route}\n\n"
                
                # If no data found at all
                if not response.strip():
                    if asked_drug_name:
                        response = f"No frequency information found for {asked_drug_name} in our records or drug database."
                    else:
                        response = "Please specify which medication you're asking about (e.g., 'how many times can I give paracetamol')."
                    if patient_id and not active_medications:
                        response += f"\nNo active medications recorded for patient {patient_id}."
            elif user_type.lower() == "patient":
                response = (
                    "**How to Administer This Medication**\n\n"
                    "Medication administration is very important for effectiveness and safety.\n\n"
                    "**NEVER modify how medication is given without consulting your doctor or pharmacist.**\n\n"
                    "Important points:\n"
                    "- Do NOT crush, break, or chew tablets unless told by your doctor\n"
                    "- Some medicines should be taken with food, others on empty stomach\n"
                    "- Do NOT mix medication with food or drinks without permission\n"
                    "- If your child vomits or spits out medicine, follow your doctor's advice\n"
                    "- If your child refuses medicine, talk to your pharmacist about alternatives (like liquid form)\n\n"
                    "**Please consult your doctor or pharmacist about:**\n"
                    "- How to give this specific medication\n"
                    "- Whether it can be crushed or mixed\n"
                    "- Whether to take with food or on empty stomach\n"
                    "- What to do if your child vomits after taking it\n"
                )
            else:
                response = (
                    "**Medication Administration Guidance**\n\n"
                    "For specific administration concerns:\n"
                    "- Verify pharmacy label for administration instructions\n"
                    "- Check drug formulation (extended-release, enteric-coated, etc.)\n"
                    "- Consider crushing tablets only if appropriate formulation\n"
                    "- Advise patient on food interactions if any\n"
                    "- Provide written instructions if administration is complex\n"
                )
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "user_type": user_type,
                "intent": "MEDICATION_ADMINISTRATION_QUERY",
                "question": user_question,
                "response": response,
                "sources": ["Medication Administration Guidelines"],
                "patient_id": patient_id
            }
            self.save_response(result)
            logger.info(f"[MED_ADMIN] Administration guidance provided")
            return result

        # ====================================================================
        # MEDICATION_SIDE_EFFECTS_QUERY: "What are the side effects?"
        # Uses extract_drug_information() to get real data from JSON KB + FDA API
        # ====================================================================
        if intent == "MEDICATION_SIDE_EFFECTS_QUERY":
            logger.info(f"[MED_SIDEEFF] Medication side effects query detected")
            
            # Extract drug name using the comprehensive extractor
            drug_name = extract_drug_name(user_question)
            
            if drug_name:
                logger.info(f"[MED_SIDEEFF] Drug identified: {drug_name}, fetching info from KB + FDA API")
                try:
                    info_response = extract_drug_information(user_question, drug_name)
                    if info_response:
                        if user_type.lower() == "patient":
                            # Add patient-friendly wrapper
                            response = (
                                f"**Drug Information: {drug_name.title()}**\n\n"
                                f"{info_response}\n\n"
                                "**Note:** This is general drug information. Your child's specific risks "
                                "depend on their age, weight, and health.\n\n"
                                "**Contact your doctor if your child experiences any unusual symptoms "
                                "after taking this medication.**"
                            )
                        else:
                            response = info_response
                        
                        result = self._build_result(user_type, "MEDICATION_SIDE_EFFECTS_QUERY",
                                                    user_question, response,
                                                    ["Drug Knowledge Base", "FDA OpenFDA API"], patient_id)
                        self.save_response(result)
                        logger.info(f"[MED_SIDEEFF] Drug information provided from KB + FDA API")
                        return result
                except Exception as e:
                    logger.error(f"[MED_SIDEEFF] Error fetching drug information: {e}")
            
            # Fallback: no drug name found or extraction failed
            if user_type.lower() == "patient":
                response = (
                    "**Medication Side Effects**\n\n"
                    "I could not identify the specific medication in your question.\n\n"
                    "Please specify the medication name, for example:\n"
                    "- \"What are the side effects of paracetamol?\"\n"
                    "- \"Adverse effects of ibuprofen\"\n\n"
                    "**If your child is experiencing side effects, contact your doctor immediately.**"
                )
            else:
                response = (
                    "**Medication Side Effects**\n\n"
                    "Could not identify the specific drug in your query.\n\n"
                    "Please specify the drug name, for example:\n"
                    "- \"What are the side effects of rifampicin?\"\n"
                    "- \"Adverse effects of amoxicillin\"\n"
                )
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "user_type": user_type,
                "intent": "MEDICATION_SIDE_EFFECTS_QUERY",
                "question": user_question,
                "response": response,
                "sources": ["Medication Side Effects Information"],
                "patient_id": patient_id
            }
            self.save_response(result)
            logger.info(f"[MED_SIDEEFF] Side effects information provided")
            return result

        # ====================================================================
        # VITALS_QUERY: "What's my child's weight/height/blood pressure/growth?"
        # ====================================================================
        if intent == "VITALS_QUERY":
            logger.info(f"[VITALS] Vitals/Growth query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    # Retrieve patient data if not already loaded
                    if not context_data.get("patient_data"):
                        validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                        if validation_status is True:
                            try:
                                patient_data = self.sql_agent.query_patient_record(patient_id)
                                context_data["patient_data"] = patient_data
                                logger.info(f"[VITALS] Patient data retrieved for {patient_id}")
                            except Exception as e:
                                logger.error(f"[VITALS] Error retrieving patient data: {e}")
                    
                    if context_data.get("patient_data"):
                        patient_data = context_data["patient_data"]
                        patient_info_data = patient_data.get("patient", {}).get("data", [])
                        
                        # Extract patient info
                        patient_name = None
                        birthdate = None
                        age_info = None
                        if patient_info_data:
                            patient_name = patient_info_data[0].get("given_name")
                            birthdate = patient_info_data[0].get("birthdate")
                            
                            # Calculate age info for patient view
                            if birthdate:
                                try:
                                    from dateutil.relativedelta import relativedelta
                                    birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d').date() if isinstance(birthdate, str) else birthdate
                                    age_delta = relativedelta(datetime.now().date(), birthdate_obj)
                                    age_months = age_delta.years * 12 + age_delta.months
                                    age_years = age_delta.years + age_delta.months / 12
                                    age_info = {'months': age_months, 'years': age_years}
                                except Exception as e:
                                    logger.debug(f"Error calculating age: {e}")
                        
                        # Extract vitals
                        vitals = patient_data.get("vitals", {}).get("data", [])
                        
                        # Filter vitals to only what was asked about
                        q_lower = user_question.lower()
                        vital_filters = {
                            'weight': ['weight', 'how heavy', 'weighs', 'weigh'],
                            'height': ['height', 'how tall', 'tall', 'length'],
                            'temperature': ['temperature', 'fever', 'temp'],
                            'blood pressure': ['blood pressure', 'bp', 'systolic', 'diastolic'],
                            'heart rate': ['heart rate', 'pulse', 'heartbeat'],
                            'oxygen': ['oxygen', 'spo2', 'saturation'],
                            'respiratory': ['respiratory', 'breathing rate'],
                            'head circumference': ['head circumference', 'head size'],
                            'bmi': ['bmi', 'body mass'],
                        }
                        # Check if asking for specific vitals or all
                        asked_vitals = set()
                        for category, keywords in vital_filters.items():
                            if any(kw in q_lower for kw in keywords):
                                asked_vitals.add(category)
                        
                        # Generic "vitals" / "vital signs" → show all
                        is_generic = any(kw in q_lower for kw in ['vitals', 'vital signs', 'measurements', 'growth'])
                        
                        if asked_vitals and not is_generic:
                            # Filter vitals list to only include asked-for measurements
                            filtered_vitals = []
                            for v in vitals:
                                vname = v.get('vital_name', '').lower()
                                for category in asked_vitals:
                                    if category in vname or any(kw in vname for kw in vital_filters[category]):
                                        filtered_vitals.append(v)
                                        break
                            vitals = filtered_vitals
                            logger.info(f"[VITALS] Filtered to asked vitals: {asked_vitals}")
                        
                        # Use role-based formatter
                        if user_type.lower() == "doctor":
                            response = VitalsResponseDoctor.format_vitals(
                                vitals=vitals,
                                patient_data=patient_data,
                                patient_id=patient_id,
                                patient_name=patient_name
                            )
                        else:
                            response = VitalsResponsePatient.format_vitals(
                                vitals=vitals,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "VITALS_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["Patient Vitals + OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        logger.info(f"[VITALS] Vitals information provided")
                        return result
                        
                except Exception as e:
                    logger.error(f"[VITALS] Error processing vitals query: {e}")

        # ====================================================================
        # VITALS_HISTORY_QUERY: "Show me vitals history" or "Past vital readings"
        # ====================================================================
        if intent == "VITALS_HISTORY_QUERY":
            logger.info(f"[VITALS_HISTORY] Vitals history query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    # Create database connection
                    db = OpenMRSDatabase()
                    
                    # Resolve patient identifier to internal patient_id if needed
                    resolved_patient_id = patient_id
                    
                    # If patient_id looks like an identifier, convert to internal ID
                    if not str(resolved_patient_id).isdigit():
                        # Try to resolve identifier to internal ID
                        patient_info = db.verify_patient_exists(patient_id)
                        if patient_info and patient_info.get("patient_id"):
                            resolved_patient_id = patient_info["patient_id"]
                            logger.info(f"[VITALS_HISTORY] Resolved identifier {patient_id} to internal ID {resolved_patient_id}")
                        else:
                            logger.warning(f"[VITALS_HISTORY] Could not resolve patient identifier: {patient_id}")
                    
                    # Get vitals history using internal patient ID
                    vitals_result = db.get_patient_vitals_history(resolved_patient_id, limit=100)
                    vitals_history = vitals_result.get("data", []) if isinstance(vitals_result, dict) else vitals_result
                    logger.info(f"[VITALS_HISTORY] Retrieved {len(vitals_history)} vitals records")
                    
                    # Retrieve patient data if not already loaded
                    if not context_data.get("patient_data"):
                        validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                        if validation_status is True:
                            try:
                                patient_data = self.sql_agent.query_patient_record(patient_id)
                                context_data["patient_data"] = patient_data
                                logger.info(f"[VITALS_HISTORY] Patient data retrieved for {patient_id}")
                            except Exception as e:
                                logger.error(f"[VITALS_HISTORY] Error retrieving patient data: {e}")
                    
                    patient_data = context_data.get("patient_data", {})
                    patient_info_data = patient_data.get("patient", {}).get("data", [])
                    
                    # Extract patient info
                    patient_name = None
                    birthdate = None
                    age_info = None
                    if patient_info_data:
                        patient_name = patient_info_data[0].get("given_name")
                        birthdate = patient_info_data[0].get("birthdate")
                        
                        # Calculate age info for patient view
                        if birthdate:
                            try:
                                from dateutil.relativedelta import relativedelta
                                birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d').date() if isinstance(birthdate, str) else birthdate
                                age_delta = relativedelta(datetime.now().date(), birthdate_obj)
                                age_months = age_delta.years * 12 + age_delta.months
                                age_years = age_delta.years + age_delta.months / 12
                                age_info = {'months': age_months, 'years': age_years}
                            except Exception as e:
                                logger.debug(f"Error calculating age: {e}")
                    
                    # Format vitals history response
                    if vitals_history:
                        # Organize vitals by datetime and vital type
                        from collections import defaultdict
                        history_by_date = defaultdict(dict)
                        
                        # Mapping for deduplicating vital names (English versions take precedence)
                        vital_normalization = {
                            "Température (c)": "Temperature (c)",
                            "Arterial blood oxygen saturation (pulse oximeter)": "SpO2",
                        }
                        
                        for vital in vitals_history:
                            vital_date = vital.get('obs_datetime', 'Unknown Date')
                            vital_name = vital.get('vital_name', 'Unknown Vital')
                            vital_value = vital.get('value_numeric') or vital.get('value_text', 'N/A')
                            
                            # Format the value
                            if isinstance(vital_value, (int, float)):
                                vital_value = f"{vital_value:.2f}" if isinstance(vital_value, float) else str(vital_value)
                            
                            # Normalize vital name (deduplicate English/French versions)
                            if vital_name in vital_normalization:
                                vital_name = vital_normalization[vital_name]
                            
                            # Only store if not already present (English version takes priority)
                            if vital_name not in history_by_date[vital_date]:
                                history_by_date[vital_date][vital_name] = vital_value
                        
                        # Build response based on user role
                        if user_type.lower() == "doctor":
                            # Doctor view: detailed timeline with all measurements
                            response = "## Vital Signs History (Past 10 Readings)\n\n"
                            response += f"**Patient:** {patient_name or 'Unknown'}\n"
                            response += f"**Patient ID:** {patient_id}\n\n"
                            
                            response += "### Timeline of Vital Measurements:\n\n"
                            
                            # Sort by date (most recent first)
                            sorted_dates = sorted(history_by_date.keys(), reverse=True)
                            for reading_date in sorted_dates:
                                response += f"**{reading_date}**\n"
                                vitals_at_date = history_by_date[reading_date]
                                for vital_name, vital_value in sorted(vitals_at_date.items()):
                                    response += f"  - {vital_name}: {vital_value}\n"
                                response += "\n"
                        else:
                            # Patient view: simplified timeline
                            response = "## Your Vital Signs Over Time\n\n"
                            if patient_name:
                                response += f"Here are your past vital measurements:\n\n"
                            
                            # Sort by date (most recent first)
                            sorted_dates = sorted(history_by_date.keys(), reverse=True)
                            measurement_count = 0
                            for reading_date in sorted_dates:
                                response += f"**{reading_date}**\n"
                                vitals_at_date = history_by_date[reading_date]
                                for vital_name, vital_value in sorted(vitals_at_date.items()):
                                    response += f"  • {vital_name}: {vital_value}\n"
                                response += "\n"
                                measurement_count += 1
                                if measurement_count >= 10:  # Limit to 10 measurement sets for patient view
                                    break
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "VITALS_HISTORY_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["Patient Vitals History + OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        db.disconnect()
                        logger.info(f"[VITALS_HISTORY] Vitals history provided")
                        return result
                    else:
                        response = "No vitals history found for this patient."
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "VITALS_HISTORY_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["Patient Vitals History + OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        db.disconnect()
                        return result
                        
                except Exception as e:
                    logger.error(f"[VITALS_HISTORY] Error processing vitals history query: {e}")
                    try:
                        db.disconnect()
                    except:
                        pass

        # ====================================================================
        # LAB_QUERY: "What are the patient's lab results?" or "Show me lab orders"
        # ====================================================================
        if intent == "LAB_QUERY":
            logger.info(f"[LAB] Lab query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    db = OpenMRSDatabase()
                    resolved_patient_id = patient_id
                    
                    # Verify patient ID and resolve if needed
                    if not str(resolved_patient_id).isdigit():
                        patient_info = db.verify_patient_exists(patient_id)
                        if patient_info and patient_info.get("patient_id"):
                            resolved_patient_id = patient_info["patient_id"]
                            logger.info(f"[LAB] Resolved patient ID: {resolved_patient_id}")
                    
                    # Retrieve lab orders and results
                    logger.info(f"[LAB] Fetching lab orders for patient {resolved_patient_id}")
                    lab_orders_result = db.get_patient_lab_orders(resolved_patient_id, limit=50)
                    lab_orders = lab_orders_result.get("data", []) if lab_orders_result.get("error") is None else []
                    
                    logger.info(f"[LAB] Fetching lab results for patient {resolved_patient_id}")
                    lab_results_result = db.get_patient_lab_results(resolved_patient_id, limit=50)
                    lab_results = lab_results_result.get("data", []) if lab_results_result.get("error") is None else []
                    
                    logger.info(f"[LAB] Retrieved {len(lab_orders)} lab orders and {len(lab_results)} lab results")
                    
                    # Deduplicate orders by order_id (each order is unique) and remove language variants
                    deduplicated_orders = {}
                    for order in lab_orders:
                        order_id = order.get("order_id")
                        if order_id not in deduplicated_orders:
                            deduplicated_orders[order_id] = order
                    lab_orders_unique = list(deduplicated_orders.values())
                    logger.info(f"[LAB] Deduplicated to {len(lab_orders_unique)} unique lab orders")
                    
                    # Deduplicate results by concept_id, keeping most recent
                    deduplicated_results = {}
                    for result in lab_results:
                        concept_id = result.get("concept_id")
                        obs_datetime = result.get("obs_datetime", "")
                        if concept_id not in deduplicated_results:
                            deduplicated_results[concept_id] = result
                        else:
                            # Keep the more recent one
                            existing_datetime = deduplicated_results[concept_id].get("obs_datetime", "")
                            if obs_datetime > existing_datetime:
                                deduplicated_results[concept_id] = result
                    lab_results_unique = list(deduplicated_results.values())
                    logger.info(f"[LAB] Deduplicated to {len(lab_results_unique)} unique lab results")
                    
                    # Filter out vitals from lab results to show only actual test results
                    vitals_terms = [
                        'blood pressure', 'systolic', 'diastolic', 'sbp', 'dbp',
                        'temperature', 'temp', 'pulse', 'heart rate', 'respiratory rate',
                        'respiration', 'rr', 'oxygen saturation', 'spo2', 'spO2',
                        'height', 'weight', 'circumference', 'muac', 'bmi',
                        'body mass', 'immunization', 'vaccine'
                    ]
                    
                    lab_results_filtered = []
                    debug_filtered = []
                    for result in lab_results_unique:
                        test_name = result.get("test_name", "").lower()
                        is_vital = any(vital in test_name for vital in vitals_terms)
                        if not is_vital:
                            lab_results_filtered.append(result)
                        else:
                            debug_filtered.append(test_name)
                    
                    logger.info(f"[LAB] Filtered to {len(lab_results_filtered)} actual lab test results (excluded {len(lab_results_unique) - len(lab_results_filtered)} vitals)")
                    if debug_filtered:
                        logger.info(f"[LAB] Filtered test names: {debug_filtered}")
                    
                    # Format response based on user type
                    if user_type.lower() == "patient":
                        # Patient-friendly format
                        response_parts = []
                        response_parts.append("## Your Laboratory Results\n")
                        
                        # Recent lab results
                        if lab_results_filtered:
                            response_parts.append("### Recent Lab Tests\n")
                            # Sort by date descending
                            sorted_results = sorted(lab_results_filtered, key=lambda x: x.get("obs_datetime", ""), reverse=True)
                            for result in sorted_results[:10]:
                                test_name = result.get("test_name", "Unknown Test")
                                obs_datetime = result.get("obs_datetime", "Unknown date")
                                value = result.get("value_numeric") or result.get("value_text") or "No value"
                                response_parts.append(f"- **{test_name}**: {value} (as of {obs_datetime})")
                            response_parts.append("\n")
                        else:
                            response_parts.append("*No recent lab results available.*\n\n")
                        
                        # Pending lab tests (orders without results)
                        if lab_orders_unique:
                            response_parts.append("### Pending Lab Tests\n")
                            for order in lab_orders_unique[:10]:  # Limit to 10 most recent
                                test_name = order.get("test_name", "Unknown Test")
                                urgency = order.get("urgency", "Routine")
                                date_activated = order.get("date_activated", "Unknown date")
                                response_parts.append(f"- **{test_name}** - {urgency} (ordered on {date_activated})")
                            response_parts.append("\n")
                        else:
                            response_parts.append("*No pending lab tests.*\n")
                        
                        response = "".join(response_parts)
                    
                    else:
                        # Doctor view - detailed clinical format
                        response_parts = []
                        response_parts.append("## Patient Laboratory Analysis\n\n")
                        
                        # Lab orders with status
                        if lab_orders_unique:
                            response_parts.append("### Active Lab Orders\n")
                            response_parts.append("| Test Name | Urgency | Ordered Date | Status |\n")
                            response_parts.append("|-----------|---------|--------------|--------|\n")
                            for order in lab_orders_unique:
                                test_name = order.get("test_name", "Unknown")
                                urgency = order.get("urgency", "Routine")
                                date_activated = order.get("date_activated", "N/A")
                                date_stopped = order.get("date_stopped")
                                status = "Completed" if date_stopped else "Active"
                                response_parts.append(f"| {test_name} | {urgency} | {date_activated} | {status} |\n")
                            response_parts.append("\n")
                        else:
                            response_parts.append("**No lab orders on file.**\n\n")
                        
                        # Lab results with values
                        if lab_results_filtered:
                            response_parts.append("### Recent Lab Results\n\n")
                            # Sort by date descending
                            sorted_results = sorted(lab_results_filtered, key=lambda x: x.get("obs_datetime", ""), reverse=True)
                            for result in sorted_results[:15]:  # Show up to 15 most recent unique tests
                                test_name = result.get("test_name", "Unknown Test")
                                obs_datetime = result.get("obs_datetime", "Unknown")
                                value_numeric = result.get("value_numeric")
                                value_text = result.get("value_text")
                                value = value_numeric if value_numeric else value_text
                                response_parts.append(f"- **{test_name}**: {value} ({obs_datetime})\n")
                            response_parts.append("\n")
                        else:
                            response_parts.append("**No lab results available.**\n")
                        
                        response = "".join(response_parts)
                    
                    # Prepare result with metadata
                    result = {
                        "response": response,
                        "intent": "LAB_QUERY",
                        "sources": ["OpenMRS Lab Orders", "OpenMRS Lab Results"],
                        "patient_id": resolved_patient_id,
                        "context_data": {
                            "lab_orders_count": len(lab_orders),
                            "lab_results_count": len(lab_results)
                        }
                    }
                    
                    db.disconnect()
                    return result
                    
                except Exception as e:
                    logger.error(f"[LAB] Error retrieving lab data: {str(e)}", exc_info=True)
                    response = f"❌ Error retrieving lab information: {str(e)}"
                    result = {
                        "response": response,
                        "intent": "LAB_QUERY",
                        "sources": ["Error"],
                        "patient_id": patient_id
                    }
                    return result
            else:
                response = "⚠️ No patient selected. Please select a patient first."
                result = {
                    "response": response,
                    "intent": "LAB_QUERY",
                    "sources": ["Error"],
                    "patient_id": None
                }
                return result

        # ====================================================================
        # ENCOUNTERS_QUERY: "What are the patient's visits?" or "Show me encounters"
        # ====================================================================
        if intent == "ENCOUNTERS_QUERY":
            logger.info(f"[ENCOUNTERS] Encounters query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    db = OpenMRSDatabase()
                    resolved_patient_id = patient_id
                    
                    # Verify patient ID and resolve if needed
                    if not str(resolved_patient_id).isdigit():
                        patient_info = db.verify_patient_exists(patient_id)
                        if patient_info and patient_info.get("patient_id"):
                            resolved_patient_id = patient_info["patient_id"]
                            logger.info(f"[ENCOUNTERS] Resolved patient ID: {resolved_patient_id}")
                    
                    # Retrieve encounters and visits
                    logger.info(f"[ENCOUNTERS] Fetching encounters for patient {resolved_patient_id}")
                    encounters_result = db.get_patient_encounters(resolved_patient_id, limit=100)
                    encounters = encounters_result.get("data", []) if encounters_result.get("error") is None else []
                    
                    logger.info(f"[ENCOUNTERS] Retrieved {len(encounters)} encounters")
                    
                    # Get patient details (name, age, etc.)
                    patient_result = db.get_patient_by_id(resolved_patient_id)
                    patient_name = "Unknown"
                    if patient_result.get("data"):
                        patient_data = patient_result["data"][0]
                        given_name = patient_data.get("given_name", "")
                        family_name = patient_data.get("family_name", "")
                        patient_name = f"{given_name} {family_name}".strip()
                    
                    # Format response based on user type
                    if user_type.lower() == "patient":
                        # Patient-friendly format
                        response_parts = []
                        response_parts.append(f"## Your Visit History\n\n")
                        response_parts.append(f"Patient: **{patient_name}**\n\n")
                        
                        if encounters:
                            response_parts.append(f"### Recent Visits ({len(encounters)} total)\n\n")
                            # Sort by date descending (most recent first) and limit to recent 10
                            sorted_encounters = sorted(encounters, key=lambda x: x.get("encounter_datetime", ""), reverse=True)
                            for i, encounter in enumerate(sorted_encounters[:10], 1):
                                encounter_datetime = encounter.get("encounter_datetime", "Unknown date")
                                encounter_type = encounter.get("encounter_type_name", "General Visit")
                                location = encounter.get("location_id", "Unknown location")
                                response_parts.append(f"{i}. **{encounter_type}** - {encounter_datetime}\n")
                            
                            if len(sorted_encounters) > 10:
                                response_parts.append(f"\n... and {len(sorted_encounters) - 10} more visits\n")
                        else:
                            response_parts.append("*No visit records found.*\n")
                        
                        response = "".join(response_parts)
                    
                    else:
                        # Doctor view - detailed clinical format
                        response_parts = []
                        response_parts.append(f"## Patient Encounters Report\n\n")
                        response_parts.append(f"**Patient:** {patient_name}\n")
                        response_parts.append(f"**Total Encounters:** {len(encounters)}\n\n")
                        
                        if encounters:
                            response_parts.append("### Clinical Encounter History\n\n")
                            response_parts.append("| Date & Time | Encounter Type | Location | Encounter ID |\n")
                            response_parts.append("|-------------|----------------|----------|---------------|\n")
                            
                            # Sort by date descending (most recent first)
                            sorted_encounters = sorted(encounters, key=lambda x: x.get("encounter_datetime", ""), reverse=True)
                            for encounter in sorted_encounters:
                                encounter_id = encounter.get("encounter_id", "N/A")
                                encounter_datetime = encounter.get("encounter_datetime", "Unknown")
                                encounter_type = encounter.get("encounter_type_name", "General")
                                location_id = encounter.get("location_id", "N/A")
                                response_parts.append(f"| {encounter_datetime} | {encounter_type} | {location_id} | {encounter_id} |\n")
                        else:
                            response_parts.append("**No encounters documented.**\n")
                        
                        response = "".join(response_parts)
                    
                    # Prepare result with metadata
                    result = {
                        "response": response,
                        "intent": "ENCOUNTERS_QUERY",
                        "sources": ["OpenMRS Encounters"],
                        "patient_id": resolved_patient_id,
                        "context_data": {
                            "encounters_count": len(encounters)
                        }
                    }
                    
                    db.disconnect()
                    return result
                    
                except Exception as e:
                    logger.error(f"[ENCOUNTERS] Error retrieving encounter data: {str(e)}", exc_info=True)
                    response = f"❌ Error retrieving encounter information: {str(e)}"
                    result = {
                        "response": response,
                        "intent": "ENCOUNTERS_QUERY",
                        "sources": ["Error"],
                        "patient_id": patient_id
                    }
                    return result
            else:
                response = "⚠️ No patient selected. Please select a patient first."
                result = {
                    "response": response,
                    "intent": "ENCOUNTERS_QUERY",
                    "sources": ["Error"],
                    "patient_id": None
                }
                return result

        # ====================================================================
        # FUTURE_APPOINTMENTS_QUERY: "What are my upcoming appointments?"
        # ====================================================================
        if intent == "FUTURE_APPOINTMENTS_QUERY":
            logger.info(f"[FUTURE_APPTS] Future appointments query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    db = OpenMRSDatabase()
                    resolved_patient_id = patient_id
                    
                    # Verify patient ID and resolve if needed
                    if not str(resolved_patient_id).isdigit():
                        patient_info = db.verify_patient_exists(patient_id)
                        if patient_info and patient_info.get("patient_id"):
                            resolved_patient_id = patient_info["patient_id"]
                            logger.info(f"[FUTURE_APPTS] Resolved patient ID: {resolved_patient_id}")
                    
                    # Retrieve future appointments
                    logger.info(f"[FUTURE_APPTS] Fetching future appointments for patient {resolved_patient_id}")
                    appointments_result = db.get_patient_appointments_future(resolved_patient_id, limit=100)
                    appointments = appointments_result.get("data", []) if appointments_result.get("error") is None else []
                    
                    logger.info(f"[FUTURE_APPTS] Retrieved {len(appointments)} future appointments")
                    
                    # Get patient details (name, age, etc.)
                    patient_result = db.get_patient_by_id(resolved_patient_id)
                    patient_name = "Unknown"
                    if patient_result.get("data"):
                        patient_data = patient_result["data"][0]
                        given_name = patient_data.get("given_name", "")
                        family_name = patient_data.get("family_name", "")
                        patient_name = f"{given_name} {family_name}".strip()
                    
                    # Format response based on user type
                    if user_type.lower() == "patient":
                        # Patient-friendly format
                        response_parts = []
                        response_parts.append(f"## Your Upcoming Appointments\n\n")
                        response_parts.append(f"Patient: **{patient_name}**\n\n")
                        
                        if appointments:
                            response_parts.append(f"### Scheduled Appointments ({len(appointments)} total)\n\n")
                            # Sort by date ascending (soonest first)
                            sorted_appointments = sorted(appointments, key=lambda x: x.get("start_date_time", ""), reverse=False)
                            for i, appt in enumerate(sorted_appointments, 1):
                                start_time = appt.get("start_date_time", "Unknown date")
                                end_time = appt.get("end_date_time", "")
                                service = appt.get("service_name", "General Appointment")
                                status = appt.get("status", "")
                                response_parts.append(f"{i}. **{service}** - {start_time}\n")
                                if status:
                                    response_parts.append(f"   Status: {status}\n")
                        else:
                            response_parts.append("*No upcoming appointments scheduled.*\n")
                        
                        response = "".join(response_parts)
                    
                    else:
                        # Doctor view - detailed format
                        response_parts = []
                        response_parts.append(f"## Patient Future Appointments Report\n\n")
                        response_parts.append(f"**Patient:** {patient_name}\n")
                        response_parts.append(f"**Upcoming Appointments:** {len(appointments)}\n\n")
                        
                        if appointments:
                            response_parts.append("### Scheduled Appointments\n\n")
                            response_parts.append("| Start Date/Time | End Date/Time | Service | Status | Location |\n")
                            response_parts.append("|-----------------|---------------|---------|--------|----------|\n")
                            
                            # Sort by date ascending (soonest first)
                            sorted_appointments = sorted(appointments, key=lambda x: x.get("start_date_time", ""), reverse=False)
                            for appt in sorted_appointments:
                                start_time = appt.get("start_date_time", "N/A")
                                end_time = appt.get("end_date_time", "N/A")
                                service = appt.get("service_name", "General")
                                status = appt.get("status", "Scheduled")
                                location = appt.get("location_id", "N/A")
                                response_parts.append(f"| {start_time} | {end_time} | {service} | {status} | {location} |\n")
                        else:
                            response_parts.append("**No upcoming appointments scheduled.**\n")
                        
                        response = "".join(response_parts)
                    
                    # Prepare result with metadata
                    result = {
                        "response": response,
                        "intent": "FUTURE_APPOINTMENTS_QUERY",
                        "sources": ["OpenMRS Appointments"],
                        "patient_id": resolved_patient_id,
                        "context_data": {
                            "appointments_count": len(appointments)
                        }
                    }
                    
                    db.disconnect()
                    return result
                    
                except Exception as e:
                    logger.error(f"[FUTURE_APPTS] Error retrieving appointment data: {str(e)}", exc_info=True)
                    response = f"❌ Error retrieving appointment information: {str(e)}"
                    result = {
                        "response": response,
                        "intent": "FUTURE_APPOINTMENTS_QUERY",
                        "sources": ["Error"],
                        "patient_id": patient_id
                    }
                    return result
            else:
                response = "⚠️ No patient selected. Please select a patient first."
                result = {
                    "response": response,
                    "intent": "FUTURE_APPOINTMENTS_QUERY",
                    "sources": ["Error"],
                    "patient_id": None
                }
                return result

        # ====================================================================
        if intent == "IMMUNIZATION_QUERY":
            logger.info(f"[IMMUNIZATION] Immunization query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    immun_fetcher = ImmunizationOpenMRSFetcher()
                    
                    # Analyze the question to determine what data to fetch
                    question_lower = user_question.lower()
                    
                    # PRIORITY 1: Check if asking for LAST/HISTORY (highest priority)
                    asking_for_history = any(phrase in question_lower for phrase in [
                        'last', 'latest', 'recent', 'most recent', 'received', 'given', 'history', 'had', 'took', 'administered'
                    ])
                    
                    # PRIORITY 2: Check if asking for MISSED
                    asking_for_missed = any(phrase in question_lower for phrase in [
                        'missed', 'overdue', 'behind', 'not given', 'not received', 'required'
                    ])
                    
                    # PRIORITY 3: Check if asking for NEXT (lowest priority to avoid "when" interfering with "when...last")
                    asking_for_next_dose = (not asking_for_history) and any(phrase in question_lower for phrase in [
                        'next', 'scheduled', 'when', 'appointment', 'due', 'upcoming', 'future'
                    ])
                    
                    # Get patient info if not already loaded
                    patient_name = None
                    age_info = None
                    if not context_data.get("patient_data"):
                        validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                        if validation_status is True:
                            try:
                                patient_data = self.sql_agent.query_patient_record(patient_id)
                                context_data["patient_data"] = patient_data
                            except Exception as e:
                                logger.debug(f"Could not retrieve patient data: {e}")
                    
                    if context_data.get("patient_data"):
                        try:
                            patient_info_data = context_data["patient_data"].get("patient", {}).get("data", [])
                            if patient_info_data:
                                patient_name = patient_info_data[0].get("given_name")
                                birthdate_str = patient_info_data[0].get("birthdate")
                                
                                # Calculate age
                                if birthdate_str:
                                    from dateutil.relativedelta import relativedelta
                                    birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date() if isinstance(birthdate_str, str) else birthdate_str
                                    age_delta = relativedelta(datetime.now().date(), birthdate)
                                    age_months = age_delta.years * 12 + age_delta.months
                                    age_years = age_delta.years + age_delta.months / 12
                                    age_info = {'months': age_months, 'years': age_years}
                        except Exception as e:
                            logger.debug(f"Error extracting patient info: {e}")
                    
                    # Fetch appropriate data based on question type
                    if asking_for_next_dose:
                        logger.info(f"[IMMUNIZATION] Question asks for NEXT SCHEDULED DOSE")
                        next_scheduled = immun_fetcher.get_next_scheduled_dose(patient_id)
                        missed = immun_fetcher.get_missed_vaccines(patient_id)
                        history = immun_fetcher.get_immunization_history(patient_id)
                        
                        # IMPORTANT: For next dose questions, ALWAYS include missed vaccines (vaccines that are due)
                        # Even if asking_for_missed is False, missed vaccines represent the "next" vaccines to give
                        if user_type.lower() == "patient":
                            response = ImmunizationResponsePatient.format_next_scheduled_dose(
                                next_scheduled=next_scheduled,
                                missed_vaccines=missed,  # Always include - shows what's due next
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        else:  # Doctor
                            response = ImmunizationResponseDoctor.format_next_scheduled_dose(
                                next_scheduled=next_scheduled,
                                missed_vaccines=missed,  # Always include - shows what's due next
                                history=history,
                                patient_id=patient_id,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                    
                    elif asking_for_history:
                        logger.info(f"[IMMUNIZATION] Question asks for COMPLETE IMMUNIZATION HISTORY")
                        history = immun_fetcher.get_immunization_history(patient_id)
                        recommendations = immun_fetcher.get_recommended_vaccines(patient_id)
                        
                        if user_type.lower() == "patient":
                            response = ImmunizationResponsePatient.format_immunization_records(
                                history=history,
                                recommendations=recommendations,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        else:  # Doctor
                            response = ImmunizationResponseDoctor.format_immunization_records(
                                history=history,
                                recommendations=recommendations,
                                patient_id=patient_id,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                    
                    elif asking_for_missed:
                        logger.info(f"[IMMUNIZATION] Question asks for MISSED VACCINES")
                        missed = immun_fetcher.get_missed_vaccines(patient_id)
                        history = immun_fetcher.get_immunization_history(patient_id)
                        
                        if user_type.lower() == "patient":
                            response = ImmunizationResponsePatient.format_missed_vaccines(
                                missed_vaccines=missed,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        else:  # Doctor
                            response = ImmunizationResponseDoctor.format_missed_vaccines(
                                missed_vaccines=missed,
                                history=history,
                                patient_id=patient_id,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                    
                    else:
                        # Default: show full immunization record
                        logger.info(f"[IMMUNIZATION] Question asks for FULL IMMUNIZATION RECORD")
                        history = immun_fetcher.get_immunization_history(patient_id)
                        recommendations = immun_fetcher.get_recommended_vaccines(patient_id)
                        
                        if user_type.lower() == "patient":
                            response = ImmunizationResponsePatient.format_immunization_records(
                                history=history,
                                recommendations=recommendations,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        else:  # Doctor
                            response = ImmunizationResponseDoctor.format_immunization_records(
                                history=history,
                                recommendations=recommendations,
                                patient_id=patient_id,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                    
                    immun_fetcher.disconnect()
                    
                    result = {
                        "timestamp": datetime.now().isoformat(),
                        "user_type": user_type,
                        "intent": "IMMUNIZATION_QUERY",
                        "question": user_question,
                        "response": response,
                        "sources": ["Immunization Records + OpenMRS + Vaccination Schedule Database"],
                        "patient_id": patient_id
                    }
                    self.save_response(result)
                    logger.info(f"[IMMUNIZATION] Immunization information provided")
                    return result
                    
                except Exception as e:
                    logger.error(f"[IMMUNIZATION] Error processing immunization query: {e}")

        if intent == "MILESTONE_QUERY":
            # CRITICAL FIX: Get patient age if patient selected
            patient_age = None
            if patient_id and not context_data.get("patient_data"):
                validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                if validation_status is True:
                    try:
                        patient_data = self.sql_agent.query_patient_record(patient_id)
                        context_data["patient_data"] = patient_data
                        logger.info(f"Patient data retrieved for milestone query: {patient_id}")
                    except Exception as e:
                        logger.warning(f"Could not retrieve patient data for milestone: {e}")
            
            # Extract patient age from patient data
            patient_age_months = None
            if context_data.get("patient_data"):
                try:
                    patient_data = context_data["patient_data"]
                    if patient_data.get("patient") and patient_data["patient"].get("data"):
                        p = patient_data["patient"]["data"][0]
                        birthdate = p.get('birthdate')
                        if birthdate:
                            # Calculate age in MONTHS for milestone queries
                            from dateutil.relativedelta import relativedelta
                            if isinstance(birthdate, str):
                                birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d').date()
                            else:
                                birthdate_obj = birthdate
                            today = datetime.now().date()
                            age_delta = relativedelta(today, birthdate_obj)
                            patient_age_months = age_delta.years * 12 + age_delta.months
                            patient_age = age_delta.years  # Keep years for display purposes
                            logger.info(f"Patient age calculated: {patient_age} years ({patient_age_months} months) for milestone query")
                except Exception as e:
                    logger.debug(f"Could not extract patient age: {e}")
            
            try:
                # Enhanced query with patient age context if available - use MONTHS for milestone lookup
                enhanced_milestone_query = user_question
                if patient_age_months is not None:
                    enhanced_milestone_query = f"{user_question} (Patient age: {patient_age_months} months)"
                
                milestone_results = self.mcp_agent.search_milestone(enhanced_milestone_query)
                if milestone_results and milestone_results.get('count', 0) > 0:
                    milestone_results["patient_age"] = patient_age
                    milestone_results["patient_age_months"] = patient_age_months  # Store months for display
                    context_data["mcp_data"]["milestones"] = milestone_results
                    context_data["sources"].append("Milestone Database")
                    if patient_age is not None:
                        context_data["sources"].append(f"Patient Age ({patient_age} years)")
                    logger.info(f"Milestone data retrieved: {milestone_results['count']} results for {patient_age} years")
                elif milestone_results and milestone_results.get('note'):
                    # Age is beyond available milestone data
                    logger.info(f"Milestone lookup note: {milestone_results.get('note')}")
                    context_data["milestone_note"] = milestone_results.get('note')
                    context_data["patient_age"] = patient_age  # Store age for the response message
            except Exception as e:
                logger.error(f"Error searching milestones: {e}")


        # Query knowledge base - ONLY for intents that need LLM response
        try:
            if user_type == "DOCTOR":
                kb_results = self.knowledge_agent.query_doctor_kb(user_question)
                kb_content = self.knowledge_agent.format_context(kb_results)
            else:
                kb_results = self.knowledge_agent.query_patient_kb(user_question)
                kb_content = self.knowledge_agent.format_context(kb_results)

            if kb_content:
                context_data["sources"].append("Knowledge Base")
            context_data["kb_content"] = kb_content
        except Exception as e:
            logger.warning(f"Error querying knowledge base: {e}")
            context_data["kb_content"] = ""


        # Generate response
        try:
            # If this was a PATIENT_RECORD_QUERY with data, return the patient record directly
            if intent == "PATIENT_RECORD_QUERY" and context_data.get("patient_data"):
                # Pass the user question so response is filtered to what was asked
                response = self.response_agent.format_patient_data_for_llm(
                    context_data.get("patient_data"), 
                    question=user_question
                )
                # Only reject if completely empty (not based on length - short specific answers are valid)
                if not response or response == "No patient data available.":
                    response = "Patient record found but unable to format detailed data."
                logger.info(f"Returning patient record data directly")
            # If this was a PATIENT_RECORD_QUERY and we have a database error, return error response
            elif intent == "PATIENT_RECORD_QUERY" and context_data.get("db_error"):
                no_data_response = self.validation_agent.create_no_data_response(
                    context_data["db_error"]
                )
                response = self.format_response(no_data_response)
                logger.info(f"Returning error response due to database issue")
            # Special handling for milestone queries with patient age context
            elif intent == "MILESTONE_QUERY":
                if context_data.get("mcp_data", {}).get("milestones"):
                    if self.is_llm_allowed(intent):
                        response = self.response_agent.generate_milestone_response(
                            user_question,
                            context_data,
                            user_type=user_type
                        )
                    else:
                        response = "Milestone information could not be retrieved. Please contact healthcare provider."
                elif context_data.get("milestone_note"):
                    # Patient age exceeds available milestone data
                    response = f"Developmental milestone data is available only for infants and young children.\n\nCurrent patient age: {context_data.get('patient_age', 'unknown')} years\n\nFor older children and adolescents, milestones can be assessed through standardized screening tools or clinical evaluation."
                else:
                    response = "Milestone information could not be retrieved. Please contact healthcare provider."
            # Special handling for medication dose questions with patient context
            elif intent == "MEDICATION_QUERY" and user_type == "DOCTOR" and context_data.get("mcp_data", {}).get("medications"):
                response = self.response_agent.generate_medication_response_with_context(
                    user_question,
                    context_data
                )
            else:
                # For other intents, check if LLM is allowed before generating response
                if self.is_llm_allowed(intent):
                    if user_type == "DOCTOR":
                        response = self.response_agent.generate_doctor_response(user_question, context_data)
                    else:
                        response = self.response_agent.generate_patient_response(user_question, context_data)
                else:
                    # LLM blocked for this intent - return basic response from available data
                    response = "I cannot provide a detailed response for this query. Please consult your healthcare provider directly."
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            response = "Unable to generate response at this time. Please try again."

        # Ensure sources are correct
        final_sources = context_data["sources"]
        if not final_sources and context_data.get("db_error"):
            final_sources = ["No Data Available"]
        elif not final_sources:
            final_sources = ["Knowledge Base"]

        result = {
            "timestamp": datetime.now().isoformat(),
            "user_type": user_type,
            "intent": intent,
            "question": user_question,
            "response": response,
            "sources": final_sources,
            "patient_id": patient_id
        }

        self.save_response(result)
        logger.info(f"Processing complete | Sources: {', '.join(result['sources'])}")
        return result


    def save_response(self, result):
        try:
            responses = []
            if os.path.exists(RESPONSES_FILE):
                try:
                    with open(RESPONSES_FILE, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            responses = json.loads(content)
                except (json.JSONDecodeError, ValueError):
                    responses = []

            responses.append(result)

            with open(RESPONSES_FILE, 'w', encoding='utf-8') as f:
                json.dump(responses, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save response: {str(e)}")

    def select_patient(self):
        """Interactive patient selection"""
        print("\n" + "="*60)
        print("PATIENT SELECTION")
        print("="*60)
        print("\nHow would you like to search for a patient?")
        print("1. Search by Patient ID (like 1000001W or numeric)")
        print("2. Search by Patient Name")
        print("3. List all patients")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        patient_id = None
        patient_data = None
        
        if choice == "1":
            patient_id = input("Enter Patient ID (e.g., 1000001W or 8): ").strip()
            # Accept both numeric and alphanumeric IDs
            if patient_id:
                result = self.sql_agent.db.connect()
                if result:
                    patient_result = self.sql_agent.db.verify_patient_exists(patient_id)
                    self.sql_agent.db.disconnect()
                    if patient_result and patient_result is not None and patient_result is not False:
                        patient_data = patient_result
                        actual_id = patient_result.get('patient_identifier', patient_result.get('patient_id', patient_id))
                        logger.info(f"Found patient: {actual_id}")
                    else:
                        print(f"[ERROR] No patient found with ID: {patient_id}")
                        return None, None
                else:
                    print("[ERROR] Could not connect to database")
                    return None, None
            else:
                print("[ERROR] Please enter a valid patient ID")
                return None, None
                
        elif choice == "2":
            patient_name = input("Enter Patient Name (First or Last): ").strip()
            if len(patient_name) < 2:
                print("[ERROR] Please enter at least 2 characters")
                return None, None
            
            result = self.sql_agent.db.connect()
            if result:
                search_result = self.sql_agent.db.search_patients(patient_name)
                self.sql_agent.db.disconnect()
                
                if search_result['data'] and len(search_result['data']) > 0:
                    print(f"\n[FOUND] {len(search_result['data'])} patient(s):")
                    for i, patient in enumerate(search_result['data'], 1):
                        full_name = self.format_full_name(patient)
                        patient_id_display = patient.get('patient_identifier', patient.get('patient_id', 'N/A'))
                        print(f"  {i}. ID: {patient_id_display:>10} | {full_name:25} | Gender: {patient.get('gender', 'N/A'):6} | DOB: {patient.get('birthdate', 'N/A')}")
                    
                    selection = input("\nSelect patient number (or 0 to go back): ").strip()
                    if selection.isdigit() and 0 < int(selection) <= len(search_result['data']):
                        selected = search_result['data'][int(selection) - 1]
                        # Use patient_identifier if available, otherwise use patient_id
                        patient_id = selected.get('patient_identifier', str(selected.get('patient_id')))
                        # Now get full patient details
                        result = self.sql_agent.db.connect()
                        if result:
                            patient_result = self.sql_agent.db.verify_patient_exists(patient_id)
                            self.sql_agent.db.disconnect()
                            if patient_result and patient_result is not False and patient_result is not None:
                                patient_data = patient_result
                                logger.info(f"Selected patient: {patient_id}")
                else:
                    print(f"[ERROR] No patients found matching: {patient_name}")
                    return None, None
                    
        elif choice == "3":
            result = self.sql_agent.db.connect()
            if result:
                search_result = self.sql_agent.db.list_all_patients(20)
                self.sql_agent.db.disconnect()
                
                if search_result['data']:
                    print(f"\nShowing first 20 patients:")
                    for i, patient in enumerate(search_result['data'][:20], 1):
                        full_name = self.format_full_name(patient)
                        patient_id_display = patient.get('patient_identifier', patient.get('patient_id', 'N/A'))
                        print(f"  {i:>2}. ID: {patient_id_display:>10} | {full_name:25} | {patient.get('gender', 'N/A'):6} | {patient.get('birthdate', 'N/A')}")
                    
                    selection = input("\nEnter patient ID to select (or 0 to go back): ").strip()
                    if selection and selection != "0":
                        patient_id = selection
                        result = self.sql_agent.db.connect()
                        if result:
                            patient_result = self.sql_agent.db.verify_patient_exists(patient_id)
                            self.sql_agent.db.disconnect()
                            if patient_result and patient_result is not False and patient_result is not None:
                                patient_data = patient_result
                                logger.info(f"Selected patient: {patient_id}")
                            else:
                                print(f"[ERROR] Could not load patient details")
                                return None, None
        else:
            print("[ERROR] Invalid option")
            return None, None
        
        return patient_id, patient_data

    def display_patient_details(self, patient_id, patient_data):
        """Display patient information"""
        if not patient_data:
            return
        
        print("\n" + "="*60)
        print("PATIENT DETAILS")
        print("="*60)
        # Display the proper patient identifier
        patient_id_display = patient_data.get('patient_identifier', patient_data.get('patient_id', patient_id))
        print(f"\nPatient ID: {patient_id_display}")
        
        # Display patient name
        full_name = self.format_full_name(patient_data)
        print(f"Name: {full_name}")
        
        # Display patient age if birthdate is available
        birthdate = patient_data.get('birthdate', 'N/A')
        age = 'N/A'
        if birthdate and birthdate != 'N/A':
            try:
                from datetime import datetime, date
                if isinstance(birthdate, date):
                    birthdate_obj = birthdate
                else:
                    birthdate_obj = datetime.strptime(str(birthdate), "%Y-%m-%d").date()
                today = date.today()
                age = today.year - birthdate_obj.year
                if (today.month, today.day) < (birthdate_obj.month, birthdate_obj.day):
                    age -= 1
            except Exception as e:
                logger.warning(f"Could not calculate age: {e}")
                age = 'N/A'
        
        print(f"Age: {age}")
        print(f"Gender: {patient_data.get('gender', 'N/A')}")
        print(f"Birth Date: {patient_data.get('birthdate', 'N/A')}")
        print(f"Address: {patient_data.get('address1', 'N/A')}")
        if patient_data.get('address2'):
            print(f"         {patient_data.get('address2')}")
        print(f"City: {patient_data.get('city_village', 'N/A')}")
        print(f"State: {patient_data.get('state_province', 'N/A')}")
        print(f"Postal Code: {patient_data.get('postal_code', 'N/A')}")
        print(f"Status: {'Deceased (' + patient_data.get('death_date', '') + ')' if patient_data.get('dead') else 'Active'}")
        print("="*60)

    def run_interactive(self):
        logger.info("Interactive session started")
        
        # First, ask user to select their role
        self.select_user_role()
        
        while True:
            # Then, select a patient
            patient_id, patient_data = self.select_patient()
            
            if not patient_id:
                print("\n[INFO] Exiting chatbot.")
                break
            
            # Display patient details
            self.display_patient_details(patient_id, patient_data)
            
            # Get full patient details from database
            patient_full_info = self.sql_agent.query_patient_record(patient_id)
            
            # Now ask queries about this patient
            print("\n" + "="*60)
            print(f"QUERYING PATIENT: {patient_id}")
            print("="*60)
            print("Ask questions about this patient's medical records")
            print("Examples:")
            print("  - What are the recent observations for this patient?")
            print("  - Show me the patient's encounters")
            print("  - What conditions does this patient have?")
            print("\nCommands:")
            print("  'back'  - Select a different patient")
            print("  'exit'  - Exit the chatbot")
            print("="*60 + "\n")

            while True:
                user_input = input(f"[{self.user_role.upper()} | Patient {patient_id}] Your Question: ").strip()

                if user_input.lower() == 'exit':
                    print("Thank you for using the Clinical Chatbot. Goodbye!")
                    return

                if user_input.lower() == 'back':
                    print("\nGoing back to patient selection...\n")
                    break

                if not user_input:
                    print("Please enter a question.")
                    continue

                # Pass selected patient context directly to process_query
                result = self.process_query(user_input, selected_patient_id=patient_id)


                print("\n" + "-" * 60)
                print(f"User Type: {result['user_type']}")
                print(f"Intent: {result['intent']}")
                print(f"Patient ID: {result.get('patient_id', patient_id)}")
                print(f"Sources: {', '.join(result['sources'])}")
                print("-" * 60)
                print("\nResponse:")
                print(result['response'])
                print("-" * 60)


def main():
    logger.info("Clinical Chatbot Started")
    chatbot = ClinicalChatbot()

    import sys
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        result = chatbot.process_query(question)
        print("\n" + "=" * 60)
        print(f"User Type: {result['user_type']}")
        print(f"Intent: {result['intent']}")
        print(f"Sources: {', '.join(result['sources'])}")
        print("=" * 60)
        print("\nResponse:")
        print(result['response'])
        print("=" * 60)
    else:
        chatbot.run_interactive()


if __name__ == "__main__":
    main()