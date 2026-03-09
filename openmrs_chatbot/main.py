import json
import os
from datetime import datetime
from agents.triage_agent import TriageAgent
from agents.sql_agent import SQLAgent
from agents.mcp_agent import MCPAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.response_agent import ResponseAgent
from agents.validation_agent import ValidationAgent
from agents.drug_dosage_handler import detect_drug_intent, handle_drug_dosage_query
from agents.medication_openmrs_fetcher import MedicationOpenMRSFetcher
from agents.medication_response import MedicationResponseDoctor, MedicationResponsePatient
from agents.allergy_openmrs_fetcher import AllergyOpenMRSFetcher
from agents.allergy_response import AllergyResponseDoctor, AllergyResponsePatient
from agents.immunization_openmrs_fetcher import ImmunizationOpenMRSFetcher
from agents.immunization_response import ImmunizationResponseDoctor, ImmunizationResponsePatient
from utils.logger import setup_logger
from utils.config import RESPONSES_FILE

logger = setup_logger(__name__)


class ClinicalChatbot:
    
    def __init__(self):
        logger.info("Initializing Clinical Chatbot...")
        self.triage_agent = TriageAgent()
        self.sql_agent = SQLAgent()
        self.mcp_agent = MCPAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.response_agent = ResponseAgent()
        self.validation_agent = ValidationAgent()
        self.user_role = None  # Track user role for testing: 'doctor' or 'patient'
        logger.info("Chatbot initialized")
    
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
                self.user_role = "doctor"
                logger.info("User role selected: DOCTOR")
                print("\nYou are logged in as: DOCTOR")
                return
            elif choice == "2":
                self.user_role = "patient"
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
        """Process user query with optional selected patient context"""
        logger.info(f"Query received: {user_question}")
        
        triage_result = self.triage_agent.triage(user_question)
        # Use user's selected role if available, otherwise use triage classification
        user_type = self.user_role if self.user_role else triage_result["user_type"]
        intent = triage_result["intent"]
        # CRITICAL FIX: Use selected_patient_id from context, fallback to extracted ID
        patient_id = selected_patient_id or triage_result["patient_id"]

        context_data = {
            "sources": [],
            "kb_content": "",
            "patient_data": None,
            "mcp_data": {},
            "db_error": None  # Track database errors
        }

        # Query patient record if PATIENT_RECORD_QUERY intent
        if intent == "PATIENT_RECORD_QUERY" and patient_id:
            # First validate that the patient ID exists
            validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
            
            if validation_status is None:
                # Database connection error
                context_data["db_error"] = validation_error
                context_data["sources"] = []
                logger.warning(f"Cannot validate patient ID due to database error: {validation_error}")
            elif validation_status is False:
                # Patient not found
                context_data["db_error"] = validation_error
                context_data["sources"] = []
                logger.warning(f"Patient ID validation failed: {validation_error}")
            elif validation_status is True:
                # Patient exists, proceed with query
                try:
                    patient_data = self.sql_agent.query_patient_record(patient_id)
                    context_data["patient_data"] = patient_data
                    
                    # Validate if we actually have usable data
                    validation_result = self.validation_agent.validate_context_data(
                        context_data, intent, patient_id
                    )
                    
                    if validation_result["is_valid"]:
                        context_data["sources"] = validation_result["sources"]
                        logger.info(f"Patient record retrieved for ID: {patient_id}")
                    else:
                        # Database connection failed or no data found
                        context_data["sources"] = []
                        context_data["db_error"] = validation_result["error_message"]
                        logger.warning(f"Patient record unavailable: {validation_result['error_message']}")
                        
                except Exception as e:
                    logger.error(f"Error querying patient record: {e}")
                    context_data["db_error"] = str(e)
                    context_data["sources"] = []

        # Query medications if MEDICATION_QUERY intent
        if intent == "MEDICATION_QUERY":
            # ====================================================================
            # PATIENT SAFETY: Check if PATIENT is asking for dosage
            # Patients should NOT receive direct dosage amounts
            # ====================================================================
            dosage_keywords = ['how much', 'how many', 'what dose', 'what dosage', 'give how much', 'dose', 'dosage']
            is_asking_dosage = any(kw in user_question.lower() for kw in dosage_keywords)
            
            if user_type.lower() == "patient" and is_asking_dosage:
                logger.info(f"[PATIENT SAFETY] Patient asking for dosage - redirecting to doctor consultation")
                # For patient dosage queries, provide safety guidance instead of direct dosage
                dosage_disclaimer = (
                    "I cannot provide direct dosage amounts for your child.\n\n"
                    "IMPORTANT: Always consult your doctor or pharmacist for proper dosage.\n\n"
                    "They will determine the correct dose based on:\n"
                    "  • Your child's age and weight\n"
                    "  • The specific medication\n"
                    "  • Your child's medical history\n"
                    "  • Any allergies or contraindications\n\n"
                    "Contact your healthcare provider or pharmacist immediately for dosage guidance."
                )
                
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "user_type": user_type,
                    "intent": "MEDICATION_QUERY",
                    "question": user_question,
                    "response": dosage_disclaimer,
                    "sources": ["Safety Guidelines"],
                    "patient_id": patient_id
                }
                self.save_response(result)
                return result
            
            # CHECK: Is this asking about active medications for the patient?
            active_med_keywords = ['active', 'current', 'taking', 'prescribed']
            is_active_med_query = any(kw in user_question.lower() for kw in active_med_keywords)
            
            if is_active_med_query and patient_id:
                logger.info(f"[MEDICATIONS] Active medications query detected for patient {patient_id}")
                try:
                    # Fetch active medications directly from OpenMRS
                    med_fetcher = MedicationOpenMRSFetcher()
                    active_medications = med_fetcher.get_active_medications(patient_id)
                    med_fetcher.disconnect()
                    
                    if active_medications:
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
                        
                        # Format and return active medications
                        if user_type == "DOCTOR":
                            response = MedicationResponseDoctor.format_active_medications(
                                active_medications, 
                                patient_id, 
                                patient_name
                            )
                        else:
                            response = MedicationResponsePatient.format_active_medications(
                                active_medications,
                                patient_name
                            )
                        
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "MEDICATION_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["Active Medications + OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        logger.info(f"[MEDICATIONS] Active medications returned - {len(active_medications)} medications found")
                        return result
                    else:
                        logger.info(f"[MEDICATIONS] No active medications found for patient {patient_id}")
                        response = f"Patient {patient_id} currently has no active medications."
                        result = {
                            "timestamp": datetime.now().isoformat(),
                            "user_type": user_type,
                            "intent": "MEDICATION_QUERY",
                            "question": user_question,
                            "response": response,
                            "sources": ["OpenMRS Records"],
                            "patient_id": patient_id
                        }
                        self.save_response(result)
                        return result
                except Exception as e:
                    logger.error(f"[MEDICATIONS] Error fetching active medications: {e}")
                    # Fall through to regular medication query below
            
            # If doctor asked about medication for a specific patient, get patient data for dose calculation
            if patient_id and not context_data.get("patient_data"):
                validation_status, patient_info, validation_error = self.triage_agent.validate_patient_id(patient_id)
                if validation_status is True:
                    try:
                        patient_data = self.sql_agent.query_patient_record(patient_id)
                        context_data["patient_data"] = patient_data
                        logger.info(f"Patient data retrieved for medication dose calculation: {patient_id}")
                        
                        # ====================================================================
                        # DRUG DOSAGE HANDLER - After patient validation
                        # ====================================================================
                        # NOW that patient is validated, check if this is a drug dosage query
                        # and route to strict 9-step handler for safety-critical processing
                        logger.info(f"[HANDLER CHECK] user_type={user_type}")
                        drug_intent = detect_drug_intent(user_question)
                        logger.info(f"[HANDLER CHECK] detect_drug_intent={drug_intent}")
                        if user_type.upper() == "DOCTOR" and drug_intent:
                            logger.info("Drug dosage query detected after patient validation - activating strict 9-step handler")
                            try:
                                # Handler accepts both external identifier (100008E) and internal ID (15)
                                # It will resolve to internal ID internally via verify_patient_exists
                                # Pass pre-retrieved patient data to avoid DB reconnection issues
                                drug_response = handle_drug_dosage_query(
                                    query=user_question,
                                    patient_id=patient_id,
                                    db_connection=self.sql_agent.db,
                                    patient_data=context_data.get("patient_data")
                                )
                            except Exception as e:
                                logger.error(f"Drug dosage handler error (continuing to medication flow): {e}")
                                # Fall through to normal medication processing if handler fails
                            
                            # If handler returned a response, format it as proper result dictionary
                            if drug_response and isinstance(drug_response, str):
                                logger.info("Drug dosage handler completed - returning formatted response")
                                result = {
                                    "timestamp": datetime.now().isoformat(),
                                    "user_type": user_type,
                                    "intent": "MEDICATION_QUERY",
                                    "question": user_question,
                                    "response": drug_response,
                                    "sources": ["WHO Analgesics/Antipyretics/NSAIDs Approved List", "DoseCalculator"],
                                    "patient_id": patient_id
                                }
                                self.save_response(result)
                                return result
                    except Exception as e:
                        logger.warning(f"Could not retrieve patient data for dose calc: {e}")
            
            try:
                med_results = self.mcp_agent.search_medication(user_question)
                if med_results and med_results.get('count', 0) > 0:
                    context_data["mcp_data"]["medications"] = med_results
                    context_data["sources"].append("Medication Database (Enhanced)")
                    
                    # If we have patient data, calculate dose
                    if context_data.get("patient_data"):
                        try:
                            patient_data = context_data["patient_data"]
                            
                            # Extract weight from vitals
                            weight_kg = None
                            if patient_data.get("vitals") and patient_data["vitals"].get("data"):
                                for vital in patient_data["vitals"]["data"]:
                                    vital_name = vital.get('vital_name', '').lower()
                                    if 'weight' in vital_name:
                                        weight_kg = vital.get('value_numeric')
                                        if weight_kg:
                                            break
                            
                            # Extract age from patient demographics
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

        # Query allergies if ALLERGY_QUERY intent
        if intent == "ALLERGY_QUERY":
            logger.info(f"[ALLERGIES] Allergy query detected for patient {patient_id}")
            
            if patient_id:
                try:
                    allergy_fetcher = AllergyOpenMRSFetcher()
                    
                    # Extract drug name from question if asking about specific drug
                    drug_name = None
                    question_lower = user_question.lower()
                    
                    # Try to extract drug name with spelling variations (e.g., "can i give penicillin")
                    # Database of drug names with common spelling variations
                    drug_variations = {
                        'penicillin': ['penicillin', 'pencillin', 'penicilan'],  # Include typos
                        'amoxicillin': ['amoxicillin', 'amoxcilin'],
                        'aspirin': ['aspirin'],
                        'ibuprofen': ['ibuprofen'],
                        'paracetamol': ['paracetamol', 'acetaminophen'],
                        'sulfametoxazole': ['sulfametoxazole', 'sulfa', 'sulfamethoxazole'],
                        'sulfa': ['sulfa', 'sulfur'],
                        'latex': ['latex'],
                        'erythromycin': ['erythromycin'],
                        'tetracycline': ['tetracycline'],
                        'amoxicillin-clavulanate': ['amoxicillin-clavulanate', 'amoxicillin clavulanate']
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
                            
                            # Add detailed dosage consultation note if this is a hybrid question 
                            if is_hybrid_question:
                                dosage_note = (
                                    "\n\n" + "="*70 + "\n"
                                    "[ ABOUT THE DOSAGE/AMOUNT ]\n"
                                    "="*70 + "\n"
                                    "For the proper dosage of this medication, please consult your doctor or pharmacist.\n\n"
                                    "They will determine the correct amount based on:\n"
                                    "  - Your child's current age and weight\n"
                                    "  - The specific medical condition being treated\n"
                                    "  - Your child's other medications (drug interactions)\n"
                                    "  - Any allergies or sensitivities your child has\n"
                                    "  - Your child's kidney and liver function\n\n"
                                    "DO NOT give medications without confirming the dose with your doctor or pharmacist.\n"
                                    "Incorrect dosages can be dangerous."
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
        # MEDICATION_EMERGENCY_QUERY: "Overdose, missed dose, emergency"
        # ====================================================================
        if intent == "MEDICATION_EMERGENCY_QUERY":
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
                # Doctor query - provide clinical guidance
                response = (
                    f"**MEDICATION EMERGENCY - {emergency_type}**\n\n"
                    "Clinical guidance for this emergency requires:\n"
                    "1. Immediate patient assessment\n"
                    "2. Specific medication details\n"
                    "3. Patient's medical history and current vitals\n"
                    "4. Contact regional Poison Control Center if needed\n\n"
                    "Recommended actions:\n"
                    "- Activated charcoal (if appropriate for the medication)\n"
                    "- Supportive care and monitoring\n"
                    "- Contact pharmaceutical company for specific antidotes if needed\n"
                    "- Monitor for signs of toxicity\n"
                )
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "user_type": user_type,
                "intent": "MEDICATION_EMERGENCY_QUERY",
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
            is_frequency_question = any(kw in question_lower for kw in ['frequency', 'how often', 'times per day', 'times daily', 'dosing frequency', 'interval', 'between doses'])
            
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
                
                # Fetch active medications directly from OpenMRS
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
                
                # Format response based on user type
                if user_type.lower() == "patient":
                    if active_medications:
                        response = f"**Medication Frequency - {patient_name or 'Your Child'}**\n\n"
                        response += "**Active Medications and Their Dosing Frequency:**\n\n"
                        for idx, med in enumerate(active_medications, 1):
                            med_name = med.get('drug_name', 'Unknown')
                            frequency = med.get('frequency', 'As prescribed by your doctor')
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
                            response += f"   - Used for: {indication}\n"
                            response += f"   - Frequency: {frequency_readable}\n\n"
                        
                        response += "\n**Important:**\n"
                        response += "- Take/give the medication exactly as prescribed\n"
                        response += "- Do NOT skip doses or change the frequency without consulting your doctor\n"
                        response += "- If you miss a dose, consult your healthcare provider on what to do\n"
                        response += "- Set reminders to help you remember taking medications on schedule\n"
                    else:
                        response = "No active medications are currently recorded for your child.\n\nIf you believe your child is on medication, please verify with your healthcare provider."
                else:
                    # Doctor view
                    if active_medications:
                        response = f"**Medication Dosing Frequency - Patient {patient_name or patient_id}**\n\n"
                        response += "**Active Medications with Frequency and Indication:**\n\n"
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
                        
                        response += "**Clinical Considerations:**\n"
                        response += "- Verify dosing frequency is appropriate for patient's age and condition\n"
                        response += "- Monitor patient compliance with dosing schedule\n"
                        response += "- Adjust frequency based on clinical response and tolerability\n"
                        response += "- Review indications for continued need of medication\n"
                    else:
                        response = f"No active medications recorded for patient {patient_id}."
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
        # ====================================================================
        if intent == "MEDICATION_SIDE_EFFECTS_QUERY":
            logger.info(f"[MED_SIDEEFF] Medication side effects query detected")
            
            # Try to extract drug name
            drug_name = None
            question_lower = user_question.lower()
            
            drug_variations = {
                'paracetamol': ['paracetamol', 'acetaminophen', 'tylenol'],
                'ibuprofen': ['ibuprofen', 'brufen', 'advil'],
                'aspirin': ['aspirin'],
                'amoxicillin': ['amoxicillin'],
                'cough syrup': ['cough syrup', 'cough medicine'],
                'cold medicine': ['cold medicine', 'cold syrup'],
            }
            
            for canonical_name, variations in drug_variations.items():
                for variation in variations:
                    if variation in question_lower:
                        drug_name = canonical_name
                        break
                if drug_name:
                    break
            
            if user_type.lower() == "patient":
                if drug_name:
                    response = (
                        f"**Side Effects of {drug_name.title()}**\n\n"
                        "All medications can cause side effects in some people.\n\n"
                        "**Common side effects may include:**\n"
                        "- Stomach upset or nausea\n"
                        "- Mild rash or itching\n"
                        "- Drowsiness or headache\n"
                        "- Diarrhea or constipation\n\n"
                        "**Serious side effects (seek medical attention immediately if you notice):**\n"
                        "- Severe allergic reactions (swelling, difficulty breathing)\n"
                        "- Severe rash or hives\n"
                        "- Severe stomach pain or bleeding\n"
                        "- Fever or chills\n"
                        "- Yellowing of skin or eyes\n\n"
                        "**Note:** This is general information. Your child's specific risks depend on their age, weight, and health.\n\n"
                        "**Contact your doctor if your child experiences any unusual symptoms after taking this medication.**"
                    )
                else:
                    response = (
                        "**Medication Side Effects**\n\n"
                        "All medications can cause side effects. The side effects depend on:\n"
                        "- The specific medication\n"
                        "- Your child's age and weight\n"
                        "- Your child's health conditions\n"
                        "- Other medicines your child is taking\n\n"
                        "**Please consult your doctor or pharmacist about:**\n"
                        "- Specific side effects of your child's medication\n"
                        "- What side effects are normal vs. serious\n"
                        "- When to contact a doctor\n"
                        "- How to manage any side effects\n\n"
                        "**Seek immediate medical attention if your child has:**\n"
                        "- Difficulty breathing\n"
                        "- Severe allergic reaction\n"
                        "- Severe or persistent symptoms\n"
                    )
            else:
                response = (
                    "**Medication Side Effects Profile**\n\n"
                    f"For drug: {drug_name or 'Specific medication needed'}\n\n"
                    "Consider pharmacist/pharmacy resource for comprehensive side effect profile.\n"
                    "Assess patient for contraindications given their medical history.\n"
                    "Monitor for age-appropriate side effects in pediatric patients.\n"
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
                        if patient_info_data:
                            patient_name = patient_info_data[0].get("given_name")
                            birthdate = patient_info_data[0].get("birthdate")
                        
                        # Build response with vitals information
                        response = f"**{patient_name or 'Patient'}'s Health Metrics**\n\n"
                        
                        # Extract vitals
                        vitals = patient_data.get("vitals", {}).get("data", [])
                        if vitals:
                            response += "**Latest Vitals from Last Visit:**\n"
                            response += "-" * 70 + "\n\n"
                            
                            vital_mapping = {
                                'weight': ('Weight', 'kg'),
                                'height': ('Height', 'cm'),
                                'temperature': ('Temperature', '°C'),
                                'blood pressure systolic': ('BP Systolic', 'mmHg'),
                                'blood pressure diastolic': ('BP Diastolic', 'mmHg'),
                                'heart rate': ('Heart Rate', 'bpm'),
                                'oxygen saturation': ('Oxygen Level (O2)', '%'),
                                'respiratory rate': ('Respiratory Rate', 'breaths/min'),
                                'head circumference': ('Head Circumference', 'cm'),
                            }
                            
                            vitals_found = {}
                            for vital in vitals:
                                vital_name = vital.get('vital_name', '').lower()
                                vital_value = vital.get('value_numeric')
                                vital_date = vital.get('date_recorded', '')
                                
                                # Match vital to mapping
                                for search_key, (display_name, unit) in vital_mapping.items():
                                    if search_key in vital_name:
                                        vitals_found[display_name] = (vital_value, unit, vital_date)
                                        break
                            
                            # Display found vitals
                            for display_name, (value, unit, date) in sorted(vitals_found.items()):
                                if value:
                                    response += f"• **{display_name}:** {value} {unit}\n"
                            
                            if vitals:
                                response += f"\nRecorded on: {vitals[0].get('date_recorded', 'Unknown date')}\n\n"
                        else:
                            response += "No vitals data available.\n\n"
                        
                        # Growth and BMI assessment
                        if birthdate:
                            age_years = self.response_agent.calculate_age_from_birthdate(birthdate)
                            response += f"\n**Age-Related Assessment:**\n"
                            response += "-" * 70 + "\n"
                            response += f"• Current Age: {age_years:.1f} years\n"
                            
                            # Find weight and height for BMI
                            weight_kg = None
                            height_cm = None
                            for vital in vitals:
                                vital_name = vital.get('vital_name', '').lower()
                                if 'weight' in vital_name:
                                    weight_kg = vital.get('value_numeric')
                                elif 'height' in vital_name or 'length' in vital_name:
                                    height_cm = vital.get('value_numeric')
                            
                            # Calculate BMI if we have weight and height
                            if weight_kg and height_cm:
                                height_m = height_cm / 100
                                bmi = weight_kg / (height_m ** 2)
                                response += f"• BMI: {bmi:.1f}\n"
                                
                                # BMI assessment for children
                                if age_years < 18:
                                    response += "  (Note: BMI evaluation for children should consider age and growth charts)\n"
                                else:
                                    if bmi < 18.5:
                                        response += "  Status: Underweight\n"
                                    elif bmi < 25:
                                        response += "  Status: Normal weight\n"
                                    elif bmi < 30:
                                        response += "  Status: Overweight\n"
                                    else:
                                        response += "  Status: Obese\n"
                            
                            response += "\n**Important Notes:**\n"
                            response += "- Growth patterns are monitored over time\n"
                            response += "- Talk to your doctor if you have concerns about growth\n"
                            response += "- Normal ranges vary by age, sex, and genetics\n"
                        
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
        # IMMUNIZATION_QUERY: "What vaccines has my child received?" or "What vaccines are due?"
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
                        
                        if user_type.lower() == "patient":
                            response = ImmunizationResponsePatient.format_next_scheduled_dose(
                                next_scheduled=next_scheduled,
                                missed_vaccines=missed if asking_for_missed else [],
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        else:  # Doctor
                            response = ImmunizationResponseDoctor.format_next_scheduled_dose(
                                next_scheduled=next_scheduled,
                                missed_vaccines=missed if asking_for_missed else [],
                                history=history,
                                patient_id=patient_id,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                    
                    elif asking_for_history:
                        logger.info(f"[IMMUNIZATION] Question asks for LAST/MOST RECENT VACCINATION")
                        history = immun_fetcher.get_immunization_history(patient_id)
                        
                        if user_type.lower() == "patient":
                            response = ImmunizationResponsePatient.format_last_administered_vaccine(
                                history=history,
                                patient_name=patient_name,
                                age_info=age_info
                            )
                        else:  # Doctor
                            response = ImmunizationResponseDoctor.format_last_administered_vaccine(
                                history=history,
                                patient_id=patient_id,
                                patient_name=patient_name
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
            if context_data.get("patient_data"):
                try:
                    patient_data = context_data["patient_data"]
                    if patient_data.get("patient") and patient_data["patient"].get("data"):
                        p = patient_data["patient"]["data"][0]
                        birthdate = p.get('birthdate')
                        if birthdate:
                            patient_age = self.response_agent.calculate_age_from_birthdate(birthdate)
                            logger.info(f"Patient age calculated: {patient_age} years for milestone query")
                except Exception as e:
                    logger.debug(f"Could not extract patient age: {e}")
            
            try:
                # Enhanced query with patient age context if available
                enhanced_milestone_query = user_question
                if patient_age is not None:
                    enhanced_milestone_query = f"{user_question} (Patient age: {patient_age} years)"
                
                milestone_results = self.mcp_agent.search_milestone(enhanced_milestone_query)
                if milestone_results and milestone_results.get('count', 0) > 0:
                    milestone_results["patient_age"] = patient_age
                    context_data["mcp_data"]["milestones"] = milestone_results
                    context_data["sources"].append("Milestone Database")
                    if patient_age is not None:
                        context_data["sources"].append(f"Patient Age ({patient_age} years)")
                    logger.info(f"Milestone data retrieved: {milestone_results['count']} results for {patient_age} years")
            except Exception as e:
                logger.error(f"Error searching milestones: {e}")

        # Query knowledge base
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
            elif intent == "MILESTONE_QUERY" and context_data.get("mcp_data", {}).get("milestones"):
                response = self.response_agent.generate_milestone_response(
                    user_question,
                    context_data,
                    user_type=user_type
                )
            # Special handling for medication dose questions with patient context
            elif intent == "MEDICATION_QUERY" and user_type == "DOCTOR" and context_data.get("mcp_data", {}).get("medications"):
                response = self.response_agent.generate_medication_response_with_context(
                    user_question,
                    context_data
                )
            else:
                if user_type == "DOCTOR":
                    response = self.response_agent.generate_doctor_response(user_question, context_data)
                else:
                    response = self.response_agent.generate_patient_response(user_question, context_data)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            response = "Unable to generate response at this time. Please try again."

        # Ensure sources never default to "Self-help" when data is unavailable
        final_sources = context_data["sources"]
        if not final_sources and context_data.get("db_error"):
            final_sources = ["No Data Available"]
        elif not final_sources:
            final_sources = ["Knowledge Base"]  # Only KB if patient query failed but no DB error

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
            if os.path.exists(RESPONSES_FILE):
                with open(RESPONSES_FILE, 'r') as f:
                    responses = json.load(f)
            else:
                responses = []

            responses.append(result)

            with open(RESPONSES_FILE, 'w') as f:
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