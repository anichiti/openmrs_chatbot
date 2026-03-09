"""
Patient Query Processor
Handles flexible medication question understanding for patient/parent mode

Converts natural language variations into standardized intents and extracts entities.
Examples:
  "What medicine is Joshua taking?" → MEDICATION_LIST
  "Can I give penicillin?" → MEDICATION_SAFETY_CHECK + drug=penicillin
  "Tell me about ibuprofen" → MEDICATION_INFO + drug=ibuprofen
  "Is salbutamol safe with his allergies?" → MEDICATION_ALLERGY_CHECK + drug=salbutamol
"""

import re
from typing import Dict, List, Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PatientQueryProcessor:
    """Process patient/parent medication questions"""
    
    def __init__(self):
        """Initialize with medication synonyms and intent patterns"""
        
        # Synonym mappings - handle different ways of asking the same thing
        self.medication_synonyms = {
            'medication': ['medicine', 'drug', 'med', 'meds', 'medication', 'medicament', 'pharmaceutical'],
            'prescription': ['prescription', 'prescribed', 'prescribe', 'rx'],
            'active': ['active', 'current', 'taking', 'on'],
            'list': ['list', 'show', 'tell me', 'what are', 'what is', 'give me'],
            'safety': ['safe', 'okay', 'alright', 'good', 'harmful', 'dangerous', 'contraindicated'],
            'give': ['give', 'administer', 'prescribe', 'take'],
            'allergy': ['allergy', 'allergic', 'allergy', 'allergies', 'contraindication'],
            'dose': ['dose', 'dosage', 'amount', 'how much'],
            'frequency': ['frequency', 'how often', 'times per day', 'daily', 'hourly'],
            'side effects': ['side effect', 'side effects', 'adverse effect', 'reaction', 'effect'],
        }
        
        # Common drug names from knowledge base
        self.common_drugs = {
            'ibuprofen': ['ibuprofen', 'advil', 'motrin', 'brufen'],
            'paracetamol': ['paracetamol', 'acetaminophen', 'tylenol', 'panadol'],
            'aspirin': ['aspirin', 'asa'],
            'penicillin': ['penicillin', 'pencillin', 'penicilan'],
            'amoxicillin': ['amoxicillin', 'amoxcilin', 'amox'],
            'salbutamol': ['salbutamol', 'albuterol', 'ventolin'],
            'cough syrup': ['cough syrup', 'cough medicine', 'cough med'],
            'antibiotic': ['antibiotic', 'antibiotics'],
        }
        
        # Filler words to remove during normalization
        self.filler_words = {
            'um', 'uh', 'like', 'you know', 'so', 'basically', 'i think',
            'kind of', 'sort of', 'kinda', 'sorta', 'actually', 'really'
        }
        
        # Medication intent patterns
        self.intent_patterns = {
            'MEDICATION_LIST': {
                'keywords': [
                    'what.*med', 'what.*drug', 'what.*taking', 'current.*med',
                    'list.*med', 'show.*med', 'active.*med', 'on what med',
                    'prescri.*med', 'med.*list', 'active', 'he on', 'she on'
                ],
                'priority': 1
            },
            'MEDICATION_SAFETY_CHECK': {
                'keywords': [
                    'can i give', 'can i prescribe', 'can i use',
                    'is.*safe', 'safe.*give', 'safe.*med',
                    'is.*okay', 'okay.*give', 'okay.*med',
                    'can he take', 'can she take', 'can.*take',
                    'dangerous', 'harmful', 'contraindic'
                ],
                'priority': 0  # Higher priority (safety-critical)
            },
            'MEDICATION_ALLERGY_CHECK': {
                'keywords': [
                    'safe.*allerg', 'allerg.*safe', 'allerg.*med',
                    'allerg.*this', 'is.*allergic.*to',
                    'contraindica.*allerg', 'with.*allerg'
                ],
                'priority': 0  # Higher priority (safety-critical)
            },
            'MEDICATION_INFO': {
                'keywords': [
                    'tell me.*about', 'what.*about', 'info.*med',
                    'information.*med', 'how does.*work',
                    'what is.*for', 'used for', 'use.*med'
                ],
                'priority': 2
            },
            'MEDICATION_INTERACTION': {
                'keywords': [
                    'with.*med', 'together', 'both', 'interact',
                    'conflict', 'can i mix', 'can i combine'
                ],
                'priority': 2
            },
            'MEDICATION_DOSE': {
                'keywords': [
                    'dose', 'dosage', 'how much', 'how many',
                    'what dose', 'how many mg', 'frequency'
                ],
                'priority': 2
            },
        }
    
    def normalize_question(self, question: str) -> str:
        """
        Normalize question by removing filler words and standardizing terminology
        
        Args:
            question: Raw user question
        
        Returns:
            Normalized question text
        """
        if not question:
            return ""
        
        normalized = question.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common filler words with proper word boundaries and punctuation handling
        for filler in self.filler_words:
            # More flexible pattern that handles punctuation around fillers
            normalized = re.sub(f'\\s+{filler}\\s+|{filler}\\s+|\\s+{filler}', ' ', normalized, flags=re.IGNORECASE)
        
        # Remove extra punctuation and commas left behind
        normalized = re.sub(r',+', '', normalized)  # Remove remaining commas
        
        # Clean up remaining whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        logger.debug(f"[QUERY_PROCESSOR] Normalized: '{question}' -> '{normalized}'")
        return normalized
    
    def extract_drug_names(self, question: str) -> List[str]:
        """
        Extract drug names from question using synonym mapping
        
        Args:
            question: Normalized question text
        
        Returns:
            List of identified drug names (canonical forms)
        """
        extracted = []
        question_lower = question.lower()
        
        # Check each known drug and its variations
        for canonical_name, variations in self.common_drugs.items():
            for variation in variations:
                if variation in question_lower:
                    if canonical_name not in extracted:
                        extracted.append(canonical_name)
                    break
        
        logger.debug(f"[QUERY_PROCESSOR] Extracted drugs: {extracted}")
        return extracted
    
    def extract_patient_context(self, question: str) -> Dict[str, Optional[str]]:
        """
        Extract patient-related context from question
        
        Args:
            question: Normalized question text
        
        Returns:
            Dict with keys: patient_name, patient_pronoun, age_reference
        """
        context = {
            'patient_name': None,
            'patient_pronoun': None,  # 'he', 'she', 'my child', 'my son', etc.
            'age_reference': None,
        }
        
        question_lower = question.lower()
        
        # Extract pronouns
        if any(pronoun in question_lower for pronoun in ['he ', 'he\'', 'he,', 'his ']):
            context['patient_pronoun'] = 'he'
        elif any(pronoun in question_lower for pronoun in ['she ', 'she\'', 'she,', 'her ']):
            context['patient_pronoun'] = 'she'
        elif any(pronoun in question_lower for pronoun in ['my child', 'my son', 'my daughter', 'my kid']):
            context['patient_pronoun'] = 'child'
        
        # Extract age if mentioned
        age_pattern = r'(\d+)\s*(year|month|week|day|yo|yrs?|mos?|wks?|days?)'
        age_match = re.search(age_pattern, question_lower)
        if age_match:
            context['age_reference'] = age_match.group(0)
        
        logger.debug(f"[QUERY_PROCESSOR] Extracted context: {context}")
        return context
    
    def extract_symptom_context(self, question: str) -> List[str]:
        """
        Extract symptom context if mentioned
        
        Args:
            question: Normalized question text
        
        Returns:
            List of identified symptoms
        """
        symptoms = []
        question_lower = question.lower()
        
        symptom_keywords = [
            'fever', 'cough', 'pain', 'ache', 'headache', 'stomach',
            'rash', 'itch', 'nausea', 'vomit', 'diarrhea', 'cold',
            'flu', 'sore throat', 'cough', 'temperature', 'hot'
        ]
        
        for symptom in symptom_keywords:
            if symptom in question_lower:
                symptoms.append(symptom)
        
        return symptoms
    
    def classify_intent(self, question: str) -> Tuple[str, float]:
        """
        Classify the medication intent of the question
        
        Args:
            question: Normalized question text
        
        Returns:
            Tuple of (intent_type, confidence_score)
        
        Examples:
            "What medicine is he taking?" -> ("MEDICATION_LIST", 0.95)
            "Can I give penicillin?" -> ("MEDICATION_SAFETY_CHECK", 0.92)
            "Tell me about ibuprofen" -> ("MEDICATION_INFO", 0.88)
        """
        question_lower = question.lower()
        intent_scores = {}
        
        # Score each intent based on keyword matches
        for intent, config in self.intent_patterns.items():
            keyword_count = 0
            
            for pattern in config['keywords']:
                # Simple regex word boundary check
                if re.search(pattern, question_lower):
                    keyword_count += 1
            
            if keyword_count > 0:
                # Confidence formula: 
                # If matches >= 1, give at least 0.70 (acceptable match)
                # If matches >= 2, give 0.80+ (good match)
                # If matches >= 3+, give 0.90+ (excellent match)
                if keyword_count >= 3:
                    score = min(100, 90 + (keyword_count - 2))  # 90+ for 3+ matches
                elif keyword_count >= 2:
                    score = 80
                else:  # keyword_count >= 1
                    score = 70
                
                intent_scores[intent] = {
                    'score': score,
                    'matches': keyword_count,
                    'priority': config['priority']
                }
        
        # If no matches, return default
        if not intent_scores:
            logger.info("[QUERY_PROCESSOR] No intent matched, defaulting to MEDICATION_INFO")
            return ("MEDICATION_INFO", 0.3)
        
        # Sort by: priority (ascending), then score (descending)
        sorted_intents = sorted(
            intent_scores.items(),
            key=lambda x: (x[1]['priority'], -x[1]['score'])
        )
        
        best_intent = sorted_intents[0]
        intent_name = best_intent[0]
        confidence = min(100, best_intent[1]['score']) / 100  # Normalize to 0-1
        
        logger.info(
            f"[QUERY_PROCESSOR] Intent: {intent_name} "
            f"| Confidence: {confidence:.2f} "
            f"| Matches: {best_intent[1]['matches']}"
        )
        
        return (intent_name, confidence)
    
    def process_query(self, question: str, patient_id: Optional[str] = None) -> Dict:
        """
        Process complete patient medication query
        
        Args:
            question: Raw user question
            patient_id: Patient external ID (optional, for context)
        
        Returns:
            Dict with:
            - normalized_question: Processed question text
            - intent: Type of medication query
            - confidence: Intent confidence score (0-1)
            - drug_names: List of identified drugs
            - patient_context: Patient info from question
            - symptoms: Mentioned symptoms
            - processed: True if successfully processed
        
        Example Response:
        {
            'normalized_question': 'what medicine is joshua taking',
            'intent': 'MEDICATION_LIST',
            'confidence': 0.95,
            'drug_names': [],
            'patient_context': {
                'patient_name': 'joshua',
                'patient_pronoun': 'child',
                'age_reference': '5 year'
            },
            'symptoms': [],
            'processed': True
        }
        """
        try:
            # Step 1: Normalize the question
            normalized = self.normalize_question(question)
            
            # Step 2: Classify intent
            intent, confidence = self.classify_intent(normalized)
            
            # Step 3: Extract entities
            drug_names = self.extract_drug_names(normalized)
            patient_context = self.extract_patient_context(normalized)
            symptoms = self.extract_symptom_context(normalized)
            
            result = {
                'normalized_question': normalized,
                'intent': intent,
                'confidence': confidence,
                'drug_names': drug_names,
                'patient_context': patient_context,
                'symptoms': symptoms,
                'processed': True,
                'original_question': question,
            }
            
            logger.info(
                f"[QUERY_PROCESSOR] Processed query: "
                f"intent={intent}, drugs={drug_names}, confidence={confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[QUERY_PROCESSOR] Error processing query: {e}")
            return {
                'normalized_question': question,
                'intent': 'MEDICATION_INFO',  # Fallback intent
                'confidence': 0.0,
                'drug_names': [],
                'patient_context': {},
                'symptoms': [],
                'processed': False,
                'error': str(e)
            }
    
    def get_intent_description(self, intent: str) -> str:
        """
        Get human-readable description of intent
        
        Args:
            intent: Intent type (e.g., 'MEDICATION_LIST')
        
        Returns:
            Readable description
        """
        descriptions = {
            'MEDICATION_LIST': 'Show current medications the patient is taking',
            'MEDICATION_SAFETY_CHECK': 'Check if a medication is safe to give',
            'MEDICATION_ALLERGY_CHECK': 'Check if medication is safe given allergies',
            'MEDICATION_INFO': 'Provide general information about a medication',
            'MEDICATION_INTERACTION': 'Check medication interactions',
            'MEDICATION_DOSE': 'Ask about medication dosing (should redirect to doctor)',
        }
        return descriptions.get(intent, 'Medication query')
