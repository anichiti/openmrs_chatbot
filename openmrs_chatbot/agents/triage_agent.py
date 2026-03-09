import sys
import os
# Fix module path issue when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ollama
from utils.logger import setup_logger
from utils.config import OLLAMA_HOST, OLLAMA_MODEL
from database.db import OpenMRSDatabase
import json
import re

logger = setup_logger(__name__)

# Configure Ollama client
ollama_client = ollama.Client(host=OLLAMA_HOST)

# Comprehensive keyword mappings for intent classification
INTENT_KEYWORDS = {
    'MEDICATION_QUERY': {
        'keywords': [
            'medication', 'drug', 'medicine', 'dosage', 'dose', 'prescription',
            'prescribe', 'paracetamol', 'acetaminophen', 'ibuprofen', 'aspirin',
            'amoxicillin', 'antibiotic', 'side effects', 'adverse effect', 'toxicity', 
            'dosing', 'mg', 'tablet', 'capsule', 'syrup', 'injection', 'intravenous', 
            'oral', 'topical', 'maximum dose', 'minimum dose', 'recommended dose', 
            'safe dose', 'pediatric dose', 'adult dose', 'drug interaction',
            # DOSAGE-SPECIFIC keywords (to distinguish from ALLERGY checks)
            'how much', 'how many', 'what dose', 'what dosage', 'how many mg',
            'how much should', 'how much can', 'amount of', 'quantity of',
            'give how much', 'give what dose', 'give how many',
            'the dose', 'the dosage', 'appropriate dose', 'correct dose',
            'fever dose', 'pain dose'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 1
    },
    'MEDICATION_INFO_QUERY': {
        'keywords': [
            'what medicine', 'what medication', 'what drug', 'prescribed medicine',
            'prescribed medication', 'medicines prescribed', 'medications prescribed',
            'current medicine', 'current medication', 'taking medicine', 'taking medication',
            'been prescribed', 'has been prescribed', 'is prescribed', 'what has',
            'what is this medicine', 'what is this medication', 'what is this drug',
            'what is prescribed', 'medicine for', 'medication for', 'drug for',
            'what is the medicine', 'what is the medication', 'what is the drug'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 1
    },
    'MEDICATION_ADMINISTRATION_QUERY': {
        'keywords': [
            'how to give', 'how should i give', 'how do i give', 'how to administer',
            'how should i take', 'how do i take', 'take medicine', 'give medicine',
            'with food', 'without food', 'on empty stomach', 'before food', 'after food',
            'crush', 'tablet', 'syrup', 'liquid', 'powder', 'capsule',
            'mix with', 'mix juice', 'mix food', 'dissolve', 'dilute',
            'spit out', 'vomited', 'vomit', 'throw up', 'refused', 'refuses', 'refuse',
            'spill', 'spilled', 'wasted', 'give again', 'repeat dose',
            'administer', 'administration', 'take with milk', 'with milk',
            'administration method', 'how to', 'should i', 'can i crush', 'can i mix',
            # Frequency/dosing frequency keywords
            'frequency', 'how often', 'how many times', 'times per day', 'times daily',
            'dosing frequency', 'dosage frequency', 'how often should', 'how often do',
            'interval', 'between doses', 'spacing'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 1
    },
    'MEDICATION_SIDE_EFFECTS_QUERY': {
        'keywords': [
            'side effects', 'side effect', 'adverse effect', 'adverse effects', 'adverse reaction',
            'reaction', 'reactions', 'toxicity', 'toxic', 'poisoning', 'poison',
            'what are the side effects', 'side effect of', 'effects of',
            'causes', 'cause', 'symptoms', 'symptom', 'problem', 'problems',
            'unusual symptoms', 'strange symptoms', 'weird symptoms',
            'diarrhea', 'constipation', 'nausea', 'vomiting', 'rash', 'fever',
            'allergy symptoms', 'allergic symptoms', 'itching', 'swelling',
            'drowsiness', 'sleep', 'sleepless', 'hyperactivity', 'active', 'inactive'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 1
    },
    'MEDICATION_EMERGENCY_QUERY': {
        'keywords': [
            'overdose', 'over dose', 'too much', 'took too much', 'given too much',
            'accidentally took', 'accidental', 'one extra dose', 'two doses', 'double dose',
            'emergency', 'urgent', 'urgent care', 'emergency room', 'er', 'call doctor',
            'poison', 'poisoning', 'toxin', 'toxic', 'overdosed',
            'missed dose', 'missed', 'forgot to give', 'forgot dose', 'did not give',
            'what should i do', 'what to do', 'what should i', 'what do i do',
            'help', 'emergency', 'urgent', 'immediate', 'immediately', 'right now'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 0  # HIGH: Safety-critical, requires immediate attention
    },
    'MEDICATION_COMPATIBILITY_QUERY': {
        'keywords': [
            'interaction', 'interactions', 'drug interaction', 'medication interaction',
            'together', 'take together', 'give together', 'at same time', 'simultaneously',
            'both', 'can i', 'can my child', 'can they', 'both medicines', 'both medications',
            'both drugs', 'along with', 'with another', 'with other medicine', 'with other medication',
            'ibuprofen and paracetamol', 'paracetamol and ibuprofen', 'cough and cold',
            'combine', 'combined', 'combined medicine', 'combined medication',
            'safe to take', 'safe to give', 'safe combination', 'compatible'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 0  # HIGH: Drug interactions are safety-critical
    },
    'ALLERGY_QUERY': {
        'keywords': [
            # REMOVE overly broad keywords: "can i give", "safe to give", "safe to use"
            # These were causing false positives with dosage questions
            'allergy', 'allergies', 'allergic', 'contraindication', 'contraindicated',
            'reaction', 'allergic reaction', 'adverse reaction', 'side reaction',
            'penicillin', 'sulfa', 'latex', 'allergen', 'allergenic',
            'anaphylaxis', 'anaphylactic', 'allergy history', 'allergy profile',
            'medication allergy', 'drug allergy', 'is the patient allergic',
            'allergic to', 'allergy to', 'allergies to',
            'can they take', 'can they use', 'can they take paracetamol',
            'safe medication', 'safe drug', 'contraindicated drug',
            'avoid medication', 'avoid drug', 'which medication', 'which drug',
            'is it safe', 'is it safe to give', 'is it safe to take',
            'what medications can i', 'which medications can i', 'what drugs can i',
            'list the allergy', 'list the allergies', 'show allergy', 'show allergies'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 0  # CRITICAL: Safety-critical feature, higher priority
    },
    'IMMUNIZATION_QUERY': {
        'keywords': [
            'vaccine', 'vaccination', 'immunization', 'shot', 'jab',
            'mmr', 'bcg', 'polio', 'hepatitis', 'tetanus', 'dpt', 'pentavalent',
            'measles', 'rubella', 'mumps', 'rotavirus', 'pcv', 'varicella',
            'yellow fever', 'rabies', 'immunization schedule', 'vaccination schedule',
            'booster', 'dose', 'inoculation', 'immunize',
            'vaccine history', 'immunization history', 'vaccination history', 'vaccine records',
            'immunization records', 'vaccination records', 'vaccine status', 'immunization status', 'immunization taken',
            'missed vaccine', 'missed vaccines', 'missed vaccination', 'missed vaccinations',
            'overdue vaccine', 'overdue vaccines', 'overdue vaccination', 'overdue vaccinations',
            'required vaccine', 'required vaccines', 'required vaccination', 'required vaccinations',
            'next vaccine', 'next vaccination', 'next dose', 'when is next dose'
        ],
        'agent': 'MCP_IMMUNIZATION_AGENT',
        'priority': 1
    },
    'MILESTONE_QUERY': {
        'keywords': [
            'milestone', 'development', 'developmental', 'develop', 'growth', 'progress',
            'walking', 'talking', 'sitting', 'sit', 'crawling', 'crawl', 'rolling', 'roll',
            'smiling', 'smile', 'teething', 'language', 'speech', 'motor skill',
            'cognitive', 'social', 'emotional', 'recognize', 'parents',
            'month', 'year', 'age appropriate', 'normal development',
            'developmental milestones', 'without support'
        ],
        'agent': 'MCP_MILESTONE_AGENT',
        'priority': 1
    },
    'VITALS_QUERY': {
        'keywords': [
            # Weight queries
            'weight', 'how much does', 'how heavy', 'weigh', 'weighs', 'kg', 'pounds', 'lbs', 'kilos',
            'current weight', 'last weight', 'weight at', 'weight change', 'weight has',
            'weight gone up', 'weight gone down', 'gained weight', 'lost weight',
            # Height queries
            'height', 'tall', 'how tall', 'length', 'cm', 'inches', 'in', 'foot', 'feet',
            'current height', 'last height', 'height at', 'growth', 'grow',
            # Vitals queries
            'vitals', 'vital signs', 'blood pressure', 'bp', 'temperature', 'temp', 'fever',
            'heart rate', 'pulse', 'oxygen', 'o2', 'saturation', 'spo2', 'respiratory',
            'respiration rate', 'breathing rate',
            # Growth queries
            'bmi', 'body mass index', 'percentile', 'percentiles', 'growth percentile',
            'is healthy', 'is normal', 'normal for age', 'normal for their age',
            # Visit context
            'at last visit', 'at the last visit', 'last appointment', 'last checkup',
            'last visit', 'most recent', 'previous visit', 'past visit', 'last time',
            # Trend queries
            'over the past', 'over time', 'changed', 'change', 'trend', 'history', 'compared to'
        ],
        'agent': 'SQL_AGENT',
        'priority': 1
    },
    'PATIENT_RECORD_QUERY': {
        'keywords': [
            'patient record', 'medical record', 'patient chart', 'encounter', 'observation',
            'lab results', 'laboratory test', 'analysis', 'diagnosis', 'visit history', 'appointment history',
            'glucose', 'hemoglobin', 'clinical report', 'patient summary', 'medical condition',
            'condition', 'conditions', 'diagnose', 'diagnosis', 'health history'
        ],
        'agent': 'SQL_AGENT',
        'priority': 2
    }
}

class TriageAgent:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.client = ollama_client
        self.db = OpenMRSDatabase()

    def classify_user_type(self, question):
        """Classify user as DOCTOR or PATIENT using Ollama LLM"""
        # Simple keyword-based classification first
        doctor_indicators = ['patient record', 'chart', 'labs', 'diagnosis', 'clinical', 'prescribe', 'medication order']
        
        question_lower = question.lower()
        if any(ind in question_lower for ind in doctor_indicators):
            try:
                prompt = f"Is this a DOCTOR question? Q: {question}\nAnswer ONLY: yes or no"
                response = self.client.generate(model=self.model, prompt=prompt, stream=False)
                if response and 'yes' in response['response'].lower():
                    return "DOCTOR"
            except:
                pass
            return "DOCTOR"
        
        # Fallback to heuristic for non-doctor questions
        return "PATIENT"

    def classify_intent(self, question):
        """
        Classify intent with enhanced keyword detection and MCP routing.
        CRITICAL: Medication/Immunization/Milestone queries take priority over Patient Record queries.
        
        Special handling:
        - VACCINATION questions (vaccine, vaccination) → IMMUNIZATION_QUERY (PRIORITY: Check FIRST before "missed" emergency)
        - DOSAGE questions (how much, what dose) → MEDICATION_QUERY
        - ALLERGY checks (allergic to, contraindicated) → ALLERGY_QUERY
        """
        question_lower = question.lower()
        
        # PRIORITY 1: Check for vaccination-related queries FIRST to avoid false matches with "missed" emergency keyword
        vaccination_keywords = ['vaccine', 'vaccination', 'immunization', 'mmr', 'polio', 'dpt', 'tetanus', 
                               'missed vaccine', 'missed vaccines', 'missed vaccination', 'missed vaccinations',
                               'overdue vaccine', 'overdue vaccines', 'immunization schedule', 'vaccination schedule']
        has_vaccination_keyword = any(kw in question_lower for kw in vaccination_keywords)
        
        if has_vaccination_keyword:
            logger.info(f"Intent classification: IMMUNIZATION_QUERY (vaccination-specific) | Agent: MCP_IMMUNIZATION_AGENT")
            return "IMMUNIZATION_QUERY"
        
        # Special handling for frequency questions → MEDICATION_ADMINISTRATION_QUERY
        frequency_keywords = ['frequency', 'how often', 'times per day', 'times daily', 'twice daily', 'once daily', 
                             'dosing frequency', 'how many times', 'interval between']
        has_frequency_keyword = any(kw in question_lower for kw in frequency_keywords)
        
        if has_frequency_keyword:
            logger.info(f"Intent classification: MEDICATION_ADMINISTRATION_QUERY (frequency-specific) | Agent: MCP_MEDICATION_AGENT")
            return "MEDICATION_ADMINISTRATION_QUERY"
        
        # Special handling for dosage vs allergy disambiguation
        dosage_keywords = ['how much', 'how many', 'what dose', 'what dosage', 'give how much', 'give what dose']
        allergy_keywords = ['allergic', 'allergies', 'allergy', 'contraindicated', 'adverse reaction', 'anaphylaxis', 'list the allergy', 'list the allergies', 'show allergy', 'show allergies']
        
        has_dosage_keyword = any(kw in question_lower for kw in dosage_keywords)
        has_allergy_keyword = any(kw in question_lower for kw in allergy_keywords)
        
        # If question has dosage keywords but NO allergy keywords → MEDICATION_QUERY (dosage info)
        if has_dosage_keyword and not has_allergy_keyword:
            logger.info(f"Intent classification: MEDICATION_QUERY (dosage-specific) | Agent: MCP_MEDICATION_AGENT")
            return "MEDICATION_QUERY"
        
        # If question has allergy keywords → ALLERGY_QUERY (safety check)
        if has_allergy_keyword:
            logger.info(f"Intent classification: ALLERGY_QUERY (allergy-specific) | Agent: MCP_MEDICATION_AGENT")
            return "ALLERGY_QUERY"
        
        # Default: Count keyword matches for each intent
        intent_scores = {}
        for intent, config in INTENT_KEYWORDS.items():
            keyword_matches = sum(1 for kw in config['keywords'] if kw in question_lower)
            intent_scores[intent] = {
                'matches': keyword_matches,
                'priority': config['priority'],
                'agent': config['agent']
            }
        
        # Sort by matches (descending), then by priority (ascending)
        sorted_intents = sorted(
            intent_scores.items(),
            key=lambda x: (-x[1]['matches'], x[1]['priority'])
        )
        
        # If there's a strong match (>0 for MCP agents, >1 for SQL), return that intent
        for intent, score_data in sorted_intents:
            if score_data['matches'] > 0:
                logger.info(f"Intent classification: {intent} | Matches: {score_data['matches']} | Agent: {score_data['agent']}")
                return intent
        
        # Fallback to GENERAL_MEDICAL_QUERY
        logger.info("Intent classification: GENERAL_MEDICAL_QUERY (no specific keywords matched)")
        return "GENERAL_MEDICAL_QUERY"


    def extract_patient_id(self, question):
        """Extract patient ID from question using regex patterns"""
        # CRITICAL FIX: Only extract valid patient IDs (numeric + alphanumeric like 1000001W, 100008E)
        # Don't match common words that appear after 'patient' like 'age', 'name', 'record'
        
        # Common invalid words that shouldn't be patient IDs
        invalid_words = {'age', 'name', 'record', 'data', 'info', 'information', 'details', 
                        'age', 'status', 'chart', 'history', 'file', 'profile', 'summary',
                        'record', 'notes', 'vitals', 'test', 'results'}
        
        patterns = [
            # Exact patient ID pattern: "patient 100008E" or "patient: 1000001W"
            r'(?:patient|patient\s+id)[:\s]+([A-Z0-9]+)',
            # MRN pattern
            r'mrn[:\s]+([A-Za-z0-9]+)',
            # Explicit ID pattern with colon/space
            r'(?:id|patient\s+id)[:\s]+([A-Z0-9]+)',
            # Hash pattern: #123
            r'#([A-Z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                extracted_id = match.group(1).upper().strip()
                # Validate it's not a common word
                if extracted_id.lower() not in invalid_words:
                    # Additional check: patient IDs contain numbers or are formatted (like 1000001W)
                    if any(c.isdigit() for c in extracted_id):
                        logger.info(f"Extracted patient ID: {extracted_id}")
                        return extracted_id
        return None
    
    def validate_patient_id(self, patient_id):
        """
        Validate if patient ID exists in OpenMRS database
        Returns: (is_valid: bool, patient_info: dict or None, error_message: str or None)
        """
        if not patient_id:
            return False, None, "No patient ID provided"
        
        try:
            patient_info = self.db.verify_patient_exists(patient_id)
            
            if patient_info is None:
                # Database error - connection failed
                return None, None, "Database connection failed - cannot validate patient ID"
            elif patient_info is False:
                # Patient does not exist
                return False, None, f"Patient ID '{patient_id}' not found in database"
            else:
                # Patient exists
                logger.info(f"Patient ID {patient_id} validated successfully")
                return True, patient_info, None
        except Exception as e:
            logger.warning(f"Error validating patient ID {patient_id}: {e}")
            return None, None, f"Error validating patient ID: {str(e)}"
    
    def search_patient_by_name(self, name):
        """Search for patients by name in database"""
        try:
            result = self.db.search_patients(name, limit=10)
            if result.get("error"):
                return None
            
            patients = result.get("data", [])
            if patients:
                return patients
            return []
        except Exception as e:
            logger.warning(f"Error searching for patients: {e}")
            return None
    
    def _classify_user_type_heuristic(self, question):
        """Fallback heuristic-based user classification when model fails"""
        doctor_keywords = ['patient record', 'chart', 'labs', 'diagnosis', 'clinical notes', 'medication order']
        question_lower = question.lower()
        
        for keyword in doctor_keywords:
            if keyword in question_lower:
                return "DOCTOR"
        return "PATIENT"
    
    def _classify_intent_heuristic(self, question):
        """Fallback heuristic-based intent classification when model fails"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['medication', 'drug', 'medicine', 'dosage', 'prescription']):
            return 'MEDICATION_QUERY'
        elif any(word in question_lower for word in ['vaccine', 'immunization', 'shot', 'vaccination']):
            return 'IMMUNIZATION_QUERY'
        elif any(word in question_lower for word in ['milestone', 'development', 'growth', 'progress']):
            return 'MILESTONE_QUERY'
        elif any(word in question_lower for word in ['patient', 'record', 'chart', 'encounter', 'visit', 'observation']):
            return 'PATIENT_RECORD_QUERY'
        else:
            return 'GENERAL_MEDICAL_QUERY'

    def get_agent_for_intent(self, intent):
        """Get the MCP/SQL agent that should be triggered for this intent"""
        for intent_key, config in INTENT_KEYWORDS.items():
            if intent_key == intent:
                return config['agent']
        return None
    
    def triage(self, question):
        """Triage the question to determine user type, intent, patient ID, and required agent"""
        user_type = self.classify_user_type(question)
        intent = self.classify_intent(question)
        patient_id = self.extract_patient_id(question)
        agent = self.get_agent_for_intent(intent)

        triage_result = {
            "user_type": user_type,
            "intent": intent,
            "patient_id": patient_id,
            "question": question,
            "agent": agent
        }
        logger.info(f"Triage: {user_type} | Intent: {intent} | Agent: {agent} | Patient: {patient_id or 'N/A'}")
        return triage_result
