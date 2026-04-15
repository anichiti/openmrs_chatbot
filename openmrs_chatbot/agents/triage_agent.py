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
    'MEDICATION_EMERGENCY': {
        'keywords': [
            'overdose', 'over dose', 'too much', 'took too much', 'given too much',
            'accidentally took', 'accidental', 'one extra dose', 'two doses', 'double dose',
            'emergency', 'urgent', 'urgent care', 'emergency room', 'call doctor',
            'poison', 'poisoning', 'toxin', 'toxic', 'overdosed',
            'missed dose', 'forgot to give', 'forgot dose', 'did not give',
            'what should i do', 'what to do', 'what should i', 'what do i do',
            'immediate', 'immediately', 'right now'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 0  # HIGH: Safety-critical, requires immediate attention
    },
    'MEDICATION_COMPATIBILITY_QUERY': {
        'keywords': [
            'interaction', 'interactions', 'drug interaction', 'medication interaction',
            'together', 'take together', 'give together', 'at same time', 'simultaneously',
            'both medicines', 'both medications',
            'both drugs', 'along with', 'with another', 'with other medicine', 'with other medication',
            'ibuprofen and paracetamol', 'paracetamol and ibuprofen', 'cough and cold',
            'combine', 'combined', 'combined medicine', 'combined medication',
            'safe combination', 'compatible'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 0  # HIGH: Drug interactions are safety-critical
    },
    'PAST_MEDICATIONS_QUERY': {
        'keywords': [
            'past medication', 'past medications', 'previous medication', 'previous medications',
            'before', 'discontinued medication', 'discontinued medications', 'stopped medication',
            'stopped taking', 'was on', 'used to take', 'used to give', 'previously on',
            'previously given', 'previously took', 'had been on', 'was prescribed',
            'earlier medication', 'earlier medications', 'old medication', 'former medication',
            'medication history', 'medications history', 'what medication was', 'what medications were',
            'any previous medicine', 'any prior medicine', 'what was given before'
        ],
        'agent': 'MCP_MEDICATION_AGENT',
        'priority': 1
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
            'avoid medication', 'avoid drug', 'avoid medicine', 'should avoid',
            'should child avoid', 'medicines should avoid', 'which medication', 'which drug',
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
            'height', 'tall', 'how tall', 'length', 'cm', 'inches', 'foot', 'feet',
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
            'condition', 'conditions', 'diagnose', 'diagnosis', 'health history',
            # Basic demographic queries
            'name', 'patient name', 'what is the name', 'who is the patient',
            'age', 'how old', 'years old', 'patient age',
            'gender', 'sex', 'male', 'female',
            'birthdate', 'birth date', 'date of birth', 'dob', 'born',
            'address', 'where does', 'city', 'state', 'postal code',
            'status', 'deceased', 'alive', 'active',
            # General patient info queries
            'patient info', 'patient information', 'patient details', 'patient data',
            'tell me about', 'show me', 'details'
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
        """
        Classify user as DOCTOR or PATIENT using enhanced keyword detection + LLM confirmation
        
        IMPORTANT: The same question can come from both doctor and patient.
        - Doctor asking: "What are the missed vaccinations?" → wants clinical assessment
        - Parent asking: "What are the missed vaccinations?" → wants simple list
        
        But BOTH should get the SAME DATA - only response formatting differs.
        We classify user type to determine response FORMAT, not data access.
        
        CRITICAL FIX: Parent/Child keywords OVERRIDE generic clinical keywords like "temperature"
        """
        question_lower = question.lower()
        
        # PARENT/CAREGIVER indicators - HIGH PRIORITY (checked FIRST to override clinical keywords)
        parent_indicators = [
            'my child', 'my son', 'my daughter', 'my kid', 'my baby', 
            'my infant', 'my toddler', 'my newborn', 'my family',
            'as a parent', 'is my child', 'should my child', 
            'my child\'s', 'my son\'s', 'my daughter\'s', 'my baby\'s',
            'parent', 'mother', 'father', 'caregiver', 'guardian',
            'your child', 'your son', 'your daughter'
        ]
        
        # Check for parent indicators FIRST (highest priority)
        has_parent_indicator = any(ind in question_lower for ind in parent_indicators)
        if has_parent_indicator:
            logger.info(f"[TRIAGE] Parent/Caregiver indicator detected in '{question}' - classifying as PATIENT")
            return "PATIENT"
        
        # ENHANCED Doctor indicators - covers typical clinical questions/contexts
        # NOTE: Generic vital signs (temp, BP, HR, O2) are REMOVED as they're too common in parent/patient queries
        doctor_indicators = [
            # Patient/Chart terminology - STRONG doctor indicator
            'patient record', 'patient chart', 'patient summary', 'patient profile', 'patient data',
            'chart', 'clinical chart', 'medical record', 'patient notes',
            
            # Clinical assessment - STRONG doctor indicator
            'clinical', 'clinical assessment', 'clinical evaluation', 'diagnosis', 'diagnose',
            'assessment', 'evaluation', 'management', 'treatment plan', 'prognosis',
            'differential diagnosis', 'work up',
            
            # Doctor/Medical professional context - STRONG doctor indicator
            'im the doctor', 'i am the doctor', 'as a doctor', 'doctor here', 'i\'m treating',
            'prescribe', 'prescription', 'medication order', 'order medication',
            'contraindication', 'therapeutic', 'pharmacokinetics',
            
            # Lab/Investigation - STRONG doctor indicator
            'labs', 'lab results', 'lab tests', 'laboratory', 'investigation',
            'glucose', 'hemoglobin', 'bilirubin', 'creatinine',
            
            # Age/Stage specific clinical context - STRONG doctor indicator
            'pediatric assessment', 'pediatric dosing', 'age-appropriate dose',
            'developmental milestone', 'growth percentile',
            
            # Drug/Pharmacology context - STRONG doctor indicator
            'drug interaction', 'adverse effect', 'toxicity',
            'dosage calculation', 'dose adjustment',
            'allergy profile', 'contraindicated medication',
            
            # Common clinical question phrasing - STRONG doctor indicator
            'this patient', 'the patient', 'for this patient',
            'what dose', 'how much dose', 'can i give', 'can we give',
            'should i give', 'should we give', 'administer',
            'what is the dose', 'recommended dose',
            
            # Questioning style typical of doctors
            'what would be', 'how would you', 'would you recommend',
            'appropriate management', 'best approach', 'indicated for',
            'rule out'
        ]
        
        # Check for doctor indicators
        has_doctor_indicator = any(ind in question_lower for ind in doctor_indicators)
        
        if has_doctor_indicator:
            logger.info(f"[TRIAGE] Doctor indicator detected in '{question}' - classifying as DOCTOR")
            # PIPELINE FIX: Removed LLM confirmation - it always returned DOCTOR anyway
            # and added ~5-10s latency per query. Session role override handles user type now.
            return "DOCTOR"
        
        # No doctor indicators - classify as PATIENT
        logger.info(f"[TRIAGE] No doctor indicators found - classifying '{question}' as PATIENT")
        return "PATIENT"

    # Valid intents the LLM is allowed to return
    VALID_INTENTS = {
        'ALLERGY_QUERY', 'MEDICATION_QUERY', 'MEDICATION_INFO_QUERY',
        'MEDICATION_ADMINISTRATION_QUERY', 'MEDICATION_SIDE_EFFECTS_QUERY',
        'MEDICATION_EMERGENCY', 'MEDICATION_COMPATIBILITY_QUERY',
        'PAST_MEDICATIONS_QUERY', 'IMMUNIZATION_QUERY', 'MILESTONE_QUERY',
        'VITALS_QUERY', 'PATIENT_RECORD_QUERY', 'GENERAL_MEDICAL_QUERY',
    }

    def _classify_intent_llm(self, question):
        """
        Use Ollama LLM to classify intent from natural language.
        Returns the intent string or None if LLM call fails.
        """
        prompt = f"""Classify this clinical chatbot question into exactly ONE intent.

ALLERGY_QUERY — Is a drug/food safe for this patient? Allergy checks, contraindications, "can patient take X"
MEDICATION_QUERY — Drug dosage amounts, dose calculations, "how much to give"
MEDICATION_INFO_QUERY — What medications is the patient currently on/prescribed
MEDICATION_ADMINISTRATION_QUERY — How to give/take medication, dosing frequency, "how often"
MEDICATION_SIDE_EFFECTS_QUERY — Side effects or adverse effects of a medication
MEDICATION_EMERGENCY — Overdose, took too much, poisoning, urgent situations
MEDICATION_COMPATIBILITY_QUERY — Drug interactions, can two drugs be taken together
PAST_MEDICATIONS_QUERY — Past/previous/discontinued medications
IMMUNIZATION_QUERY — Vaccines, immunization history, missed/overdue vaccinations
MILESTONE_QUERY — Developmental milestones (walking, talking, crawling, motor skills)
VITALS_QUERY — Weight, height, temperature, blood pressure, pulse, BMI, growth
PATIENT_RECORD_QUERY — Patient demographics (name, age, gender, DOB, address), diagnoses, lab results
GENERAL_MEDICAL_QUERY — General medical questions not fitting above

Examples:
"can my child take penicillin" → ALLERGY_QUERY
"how much paracetamol for a 10kg child" → MEDICATION_QUERY
"what medications is the patient on" → MEDICATION_INFO_QUERY
"how often should I give ibuprofen" → MEDICATION_ADMINISTRATION_QUERY
"what are the side effects of amoxicillin" → MEDICATION_SIDE_EFFECTS_QUERY
"my child accidentally took two doses" → MEDICATION_EMERGENCY
"can I give ibuprofen and paracetamol together" → MEDICATION_COMPATIBILITY_QUERY
"what vaccines has my child received" → IMMUNIZATION_QUERY
"can my baby walk at 10 months" → MILESTONE_QUERY
"what is the weight of my child" → VITALS_QUERY
"how old is the patient" → PATIENT_RECORD_QUERY
"what is croup" → GENERAL_MEDICAL_QUERY

Question: {question}

Reply with ONLY the intent name, nothing else."""

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
            )
            if response and response.get('response'):
                raw = response['response'].strip().upper()
                # Extract intent from LLM response — handle extra text/formatting
                for intent in self.VALID_INTENTS:
                    if intent in raw:
                        logger.info(f"Intent classification (LLM): {intent}")
                        return intent
                logger.warning(f"LLM returned unrecognized intent: {raw}")
                return None
            return None
        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}")
            return None

    def _classify_intent_keywords(self, question):
        """
        Keyword-based fallback intent classification.
        Used when the LLM is unavailable or returns an invalid result.
        """
        question_lower = question.lower()

        # Count keyword matches for each intent
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

        # Return the best match if any
        for intent, score_data in sorted_intents:
            if score_data['matches'] > 0:
                logger.info(f"Intent classification (keyword fallback): {intent} | Matches: {score_data['matches']}")
                return intent

        return "GENERAL_MEDICAL_QUERY"

    def classify_multi_intent(self, question):
        """
        Detect if a question contains multiple intents and return all of them.
        Returns a list of intents. If only one intent, returns a single-item list.
        """
        import re
        question_lower = question.lower()
        
        # Split on conjunctions that join separate questions
        # Use lookahead to keep the word after "and" in the second part
        split_patterns = [
            r'\band\s+also\b', r'\band\s+what\b', r'\band\s+is\b', r'\band\s+how\b',
            r'\band\s+can\b', r'\band\s+does\b', r'\band\s+has\b', r'\band\s+are\b',
            r'\band\s+tell\b', r'\band\s+show\b',
            r'\bas\s+well\s+as\b', r'\balso\s+',
        ]
        
        sub_questions = [question]
        for pattern in split_patterns:
            new_parts = []
            for part in sub_questions:
                splits = re.split(pattern, part, flags=re.IGNORECASE)
                if len(splits) > 1 and all(len(s.strip().split()) >= 2 for s in splits):
                    new_parts.extend(splits)
                else:
                    new_parts.append(part)
            sub_questions = new_parts
        
        # If we got multiple meaningful sub-questions, classify each
        if len(sub_questions) > 1:
            intents = []
            seen = set()
            for sq in sub_questions:
                sq = sq.strip()
                if len(sq.split()) < 2:
                    continue
                intent = self.classify_intent(sq)
                if intent not in seen:
                    intents.append(intent)
                    seen.add(intent)
            if intents:
                logger.info(f"Multi-intent detected: {intents} from sub-questions: {sub_questions}")
                return intents
        
        # Single intent
        return [self.classify_intent(question)]

    def classify_intent(self, question):
        """
        HYBRID intent classification: safety keyword overrides → LLM → keyword fallback.

        Layer 1: Safety-critical keyword overrides (instant, no LLM)
                 - Vaccination keywords → IMMUNIZATION_QUERY
                 - Explicit allergy words → ALLERGY_QUERY
                 - Emergency keywords → MEDICATION_EMERGENCY
        Layer 2: LLM classification (Ollama) — handles paraphrases, typos, novel phrasing
        Layer 3: Keyword scoring fallback — if LLM is unavailable or returns invalid
        """
        question_lower = question.lower()

        # ================================================================
        # LAYER 1: Safety-critical keyword overrides (NO LLM, instant)
        # These MUST be caught deterministically — never risk misclassification
        # ================================================================

        # OVERRIDE 1: Vaccination keywords → IMMUNIZATION_QUERY
        vaccination_keywords = ['vaccine', 'vaccination', 'immunization', 'mmr', 'polio', 'dpt', 'tetanus',
                               'missed vaccine', 'missed vaccines', 'missed vaccination', 'missed vaccinations',
                               'overdue vaccine', 'overdue vaccines', 'immunization schedule', 'vaccination schedule']
        if any(kw in question_lower for kw in vaccination_keywords):
            logger.info(f"Intent classification (safety override): IMMUNIZATION_QUERY")
            return "IMMUNIZATION_QUERY"

        # OVERRIDE 1.5: Drug property/information queries → MEDICATION_QUERY
        # Catches: "contraindications of paracetamol", "indications for ibuprofen",
        #          "side effects of rifampicin", "warnings for aspirin", etc.
        # These ask about DRUG PROPERTIES, not about a specific patient's allergy status.
        drug_info_terms = ['contraindication', 'indication', 'precaution',
                          'warning', 'adverse effect', 'side effect', 'drug interaction',
                          'properties of', 'information about']
        has_drug_info_term = any(term in question_lower for term in drug_info_terms)
        if has_drug_info_term:
            # Patient-specific allergy context → let ALLERGY_QUERY handle it
            patient_allergy_context = ['allergic to', 'allergy to', 'is allergic',
                                       'allergy history', 'allergy profile', 'allergy check',
                                       'check allergy', 'anaphylaxis', 'anaphylactic']
            is_patient_allergy = any(ctx in question_lower for ctx in patient_allergy_context)
            if not is_patient_allergy:
                logger.info(f"Intent classification (safety override): MEDICATION_QUERY (drug info)")
                return "MEDICATION_QUERY"

        # OVERRIDE 2: Explicit allergy words → ALLERGY_QUERY
        # NOTE: 'contraindication' removed — now handled by OVERRIDE 1.5 for drug info queries
        allergy_keywords = ['allergic', 'allergies', 'allergy', 'allergi', 'alergi', 'alerg',
                           'anaphylaxis', 'anaphylactic',
                           'allergy history', 'allergy profile', 'drug allergy', 'medication allergy']
        if any(kw in question_lower for kw in allergy_keywords):
            logger.info(f"Intent classification (safety override): ALLERGY_QUERY (allergy keyword)")
            return "ALLERGY_QUERY"

        # OVERRIDE 3: Emergency keywords → MEDICATION_EMERGENCY_QUERY
        emergency_keywords = ['overdose', 'over dose', 'took too much', 'given too much',
                             'accidentally took', 'double dose', 'poisoning', 'overdosed']
        if any(kw in question_lower for kw in emergency_keywords):
            logger.info(f"Intent classification (safety override): MEDICATION_EMERGENCY")
            return "MEDICATION_EMERGENCY"

        # OVERRIDE 4: Food/substance + safety pattern → ALLERGY_QUERY
        food_substances = ['egg', 'eggs', 'milk', 'dairy', 'peanut', 'peanuts', 'nut', 'nuts',
                          'wheat', 'gluten', 'soy', 'shellfish', 'fish', 'corn', 'gelatin', 'latex']
        food_safety_patterns = ['can i give', 'can they eat', 'can they have', 'can my child eat',
                               'can my child have', 'is it safe to give', 'is it ok to give',
                               'ok to give', 'safe to give', 'safe to eat', 'can he eat', 'can she eat',
                               'can he have', 'can she have', 'should i give', 'should i avoid']
        has_food = any(f in question_lower for f in food_substances)
        has_food_pattern = any(p in question_lower for p in food_safety_patterns)
        if has_food and has_food_pattern:
            logger.info(f"Intent classification (safety override): ALLERGY_QUERY (food/substance safety)")
            return "ALLERGY_QUERY"

        # OVERRIDE 5: Explicit vitals/growth keywords → VITALS_QUERY
        vitals_keywords = ['weight', 'height', 'how tall', 'how heavy', 'bmi', 'body mass',
                          'blood pressure', 'temperature', 'pulse', 'heart rate', 'vitals',
                          'vital signs', 'growth percentile', 'how much does he weigh',
                          'how much does she weigh', 'how much does my child weigh']
        if any(kw in question_lower for kw in vitals_keywords):
            logger.info(f"Intent classification (safety override): VITALS_QUERY")
            return "VITALS_QUERY"

        # OVERRIDE 5a: Milestone/development keywords → MILESTONE_QUERY
        milestone_keywords = ['milestone', 'developmental', 'crawl', 'crawling', 'walk', 'walking',
                             'talk', 'talking', 'sit', 'sitting', 'stand', 'standing',
                             'roll over', 'rolling', 'babbl', 'first word', 'first step',
                             'motor skill', 'fine motor', 'gross motor', 'cognitive',
                             'developmental delay', 'speech delay', 'language delay']
        if any(kw in question_lower for kw in milestone_keywords):
            logger.info(f"Intent classification (safety override): MILESTONE_QUERY")
            return "MILESTONE_QUERY"

        # OVERRIDE 5b: Demographics keywords → PATIENT_RECORD_QUERY
        # Specific terms that unambiguously mean demographics
        demographics_keywords = ['how old', 'years old', 'months old', 'date of birth',
                                 'birthdate', 'birth date', 'dob',
                                 'patient name', 'what is the name', 'who is the patient',
                                 'gender', 'patient info', 'patient record',
                                 'patient details', 'patient data', 'medical record']
        # Broader terms that could overlap with other intents
        demographics_broad = ['age', 'born', 'when was', 'address', 'where does', 'tell me about']
        # Context words indicating the question is about another domain, not demographics
        non_demographic_context = ['vaccine', 'vaccination', 'immuniz', 'allerg', 'medication',
                                   'medicine', 'drug', 'dose', 'dosage', 'side effect',
                                   'weight', 'height', 'temperature', 'blood pressure',
                                   'vitals', 'vital signs', 'bmi', 'milestone', 'walk',
                                   'talk', 'crawl', 'development']
        has_other_context = any(kw in question_lower for kw in non_demographic_context)
        
        if any(kw in question_lower for kw in demographics_keywords):
            if not has_other_context:
                logger.info(f"Intent classification (safety override): PATIENT_RECORD_QUERY (demographics)")
                return "PATIENT_RECORD_QUERY"
        if not has_other_context and any(kw in question_lower for kw in demographics_broad):
            logger.info(f"Intent classification (safety override): PATIENT_RECORD_QUERY (demographics-broad)")
            return "PATIENT_RECORD_QUERY"

        # OVERRIDE 6: Past medications keywords → PAST_MEDICATIONS_QUERY
        past_med_keywords = ['past medication', 'past medicine', 'previous medication',
                            'previously taking', 'previously prescribed', 'previously on',
                            'discontinued', 'stopped medication', 'medication history',
                            'was on', 'used to take', 'no longer on',
                            'was taking', 'was prescribed', 'were given before']
        if any(kw in question_lower for kw in past_med_keywords):
            logger.info(f"Intent classification (safety override): PAST_MEDICATIONS_QUERY")
            return "PAST_MEDICATIONS_QUERY"

        # OVERRIDE 7: Dosage frequency keywords → MEDICATION_ADMINISTRATION_QUERY
        frequency_keywords = ['how often', 'times per day', 'times daily', 'dosing frequency',
                             'how many times a day', 'how many times', 'interval between']
        if any(kw in question_lower for kw in frequency_keywords):
            logger.info(f"Intent classification (safety override): MEDICATION_ADMINISTRATION_QUERY")
            return "MEDICATION_ADMINISTRATION_QUERY"

        # OVERRIDE 8: Dosage amount keywords → MEDICATION_QUERY
        dosage_keywords = ['how much', 'what dose', 'what dosage', 'the dosage', 'dosage for',
                          'how many mg', 'recommended dose', 'safe dose', 'correct dose',
                          'appropriate dose', 'pediatric dose', 'maximum dose', 'minimum dose']
        if any(kw in question_lower for kw in dosage_keywords):
            logger.info(f"Intent classification (safety override): MEDICATION_QUERY (dosage)")
            return "MEDICATION_QUERY"

        # OVERRIDE 9: Side effects keywords → MEDICATION_SIDE_EFFECTS_QUERY
        side_effect_keywords = ['side effect', 'side effects', 'adverse effect', 'adverse effects',
                               'adverse reaction', 'what happens if', 'reactions to']
        if any(kw in question_lower for kw in side_effect_keywords):
            logger.info(f"Intent classification (safety override): MEDICATION_SIDE_EFFECTS_QUERY")
            return "MEDICATION_SIDE_EFFECTS_QUERY"

        # OVERRIDE 10: Medication info keywords → MEDICATION_INFO_QUERY
        # "what medication", "currently taking", "prescribed" without allergy/dose context
        med_info_keywords = ['what medication', 'what medicine', 'what drug',
                            'currently taking', 'currently on', 'currently prescribed',
                            'is prescribed', 'been prescribed', 'on what medication',
                            'about the medication', 'about the medicine', 'about the drug',
                            'medication list', 'medicine list']
        has_allergy_context = any(kw in question_lower for kw in ['allergy', 'allergic', 'safe', 'contraindic'])
        if any(kw in question_lower for kw in med_info_keywords) and not has_allergy_context:
            logger.info(f"Intent classification (safety override): MEDICATION_INFO_QUERY")
            return "MEDICATION_INFO_QUERY"

        # OVERRIDE 11: Drug compatibility keywords → MEDICATION_COMPATIBILITY_QUERY
        compat_keywords = ['together', 'at the same time', 'combine', 'interaction',
                          'along with', 'with another']
        has_drug_word = any(kw in question_lower for kw in ['medication', 'medicine', 'drug',
                           'ibuprofen', 'paracetamol', 'amoxicillin', 'give both'])
        if any(kw in question_lower for kw in compat_keywords) and has_drug_word:
            logger.info(f"Intent classification (safety override): MEDICATION_COMPATIBILITY_QUERY")
            return "MEDICATION_COMPATIBILITY_QUERY"

        # OVERRIDE 12: Drug safety/prescribing pattern → ALLERGY_QUERY
        # "can I prescribe X", "can I give X", "is X safe", "can my child take X"
        # Runs AFTER frequency/dosage/compatibility overrides to avoid false positives
        prescribe_safety_patterns = ['can i prescribe', 'can i give', 'can we give', 'can they take',
                                     'can my child take', 'can my kid take', 'can he take', 'can she take',
                                     'is it safe', 'safe for', 'safe to give', 'safe to take',
                                     'ok to give', 'ok to take', 'appropriate for',
                                     'should i give', 'should i prescribe', 'should we give']
        non_safety_context = ['how much', 'what dose', 'dosage', 'mg', 'how many',
                              'how often', 'times a day', 'frequency', 'together',
                              'side effect', 'adverse', 'interaction']
        has_prescribe = any(p in question_lower for p in prescribe_safety_patterns)
        has_non_safety = any(d in question_lower for d in non_safety_context)
        if has_prescribe and not has_non_safety:
            logger.info(f"Intent classification (safety override): ALLERGY_QUERY (prescribe/safety)")
            return "ALLERGY_QUERY"

        # ================================================================
        # LAYER 2: LLM classification (Ollama)
        # Handles typos, paraphrases, novel phrasing, patient-style questions
        # ================================================================
        llm_intent = self._classify_intent_llm(question)
        if llm_intent:
            return llm_intent

        # ================================================================
        # LAYER 3: Keyword scoring fallback (if LLM unavailable/failed)
        # ================================================================
        logger.warning("LLM unavailable — falling back to keyword classification")
        return self._classify_intent_keywords(question)


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
