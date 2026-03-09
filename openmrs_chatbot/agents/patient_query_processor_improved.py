"""
Enhanced Query Processor - Improved Version with Better Patterns
Addresses identified issues:
1. Better diagnosis pattern detection
2. Negation handling
3. Improved intent classification
4. Better short question handling
"""

import re
from typing import Dict, List, Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Note: To use this improved version, import from agents.patient_query_processor
# and subclass or copy the improvements

class ImprovedPatientQueryProcessor:
    """Enhanced query processor with fixes for identified issues"""
    
    def __init__(self):
        """Initialize with improved patterns"""
        
        # Synonym mappings
        self.medication_synonyms = {
            'medication': ['medicine', 'drug', 'med', 'meds'],
            'safety': ['safe', 'okay', 'alright'],
            'allergy': ['allergy', 'allergic', 'allergies'],
        }
        
        # IMPROVEMENT 1: Add negation detection
        self.negation_words = {'not', 'no', 'none', 'never', "don't", "doesn't", "didn't"}
        
        # IMPROVEMENT 2: Better diagnosis detection
        self.diagnosis_keywords = [
            'disease', 'condition', 'illness', 'asthma', 'diabetes', 'fever',
            'meningitis', 'pneumonia', 'flu', 'infection', 'allergy',
            'diagnosis'
        ]
        
        # Filler words
        self.filler_words = {
            'um', 'uh', 'like', 'you know', 'so', 'basically', 'i think',
            'kind of', 'sort of', 'kinda', 'sorta', 'actually', 'really'
        }
        
        # IMPROVEMENT 3: Expand intent patterns for edge cases
        self.improved_patterns = {
            'MEDICATION_LIST': [
                r'what.*medicin',
                r'what.*med(?!ical)',
                r'what.*drug',
                r'what.*on',
                r'currently.*on',
                r'active.*med',
                r'he.*(?:on|taking)',
                r'she.*(?:on|taking)',
                r'child.*(?:on|taking)',
                r'prescri.*med',
            ],
            'MEDICATION_SAFETY_CHECK': [
                r'can.*(?:give|use|administer|take)',
                r'is.*safe',
                r'is.*okay',
                r'is.*alright',
                r'safe.*(?:give|use)',
                r'okay.*(?:give|use)',
                r'harmful|dangerous|contraindic',
                r'should.*(?:give|use)',
                r'can.*take',
            ],
            'MEDICATION_ALLERGY_CHECK': [
                r'(?:safe|okay).*allerg',
                r'allerg.*(?:safe|okay|med)',
                r'allerg.*this',
                r'allergic.*to',
                r'contraindic.*allerg',
                r'with.*allerg',
            ],
            'MEDICATION_INFO': [
                r'tell.*about',
                r'what.*about',
                r'info.*med',
                r'information.*med',
                r'how does.*work',
                r'what.*for',
                r'used.*for',
                r'side effect',
                r'effect|reaction',
            ],
            'MEDICATION_DOSE': [
                r'dose|dosage',
                r'how.*much',
                r'how.*many',
                r'mg|tablet|capsule',
                r'frequency|often',
            ]
        }
    
    def normalize_question(self, question: str) -> str:
        """Normalize question"""
        if not question:
            return ""
        normalized = question.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        for filler in self.filler_words:
            normalized = re.sub(f'\\s+{filler}\\s+|{filler}\\s+|\\s+{filler}', ' ', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r',+', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def extract_patient_context(self, question: str) -> Dict:
        """Extract patient context"""
        context = {}
        question_lower = question.lower()
        
        # Pronoun detection
        if any(p in question_lower for p in ['he', 'his', 'him']):
            context['pronoun'] = 'he'
        elif any(p in question_lower for p in ['she', 'her']):
            context['pronoun'] = 'she'
        elif 'child' in question_lower or 'kid' in question_lower or 'son' in question_lower or 'daughter' in question_lower:
            context['pronoun'] = 'child'
        
        # Age extraction
        age_match = re.search(r'(\d+)\s*(?:year|yr|months|month)', question_lower)
        if age_match:
            context['age'] = age_match.group(1)
        
        return context
    
    def extract_symptom_context(self, question: str) -> List[str]:
        """Extract symptoms"""
        symptoms = []
        symptom_keywords = ['fever', 'cough', 'pain', 'headache', 'rash', 'nausea', 'diarrhea', 'vomiting']
        question_lower = question.lower()
        
        for symptom in symptom_keywords:
            if symptom in question_lower:
                symptoms.append(symptom)
        
        return symptoms
    
        """
        Detect if question contains negation
        
        Args:
            question: Question text
        
        Returns:
            True if negation detected
        """
        question_lower = question.lower()
        
        # Check for negation words with word boundaries
        for word in self.negation_words:
            if re.search(rf'\b{word}\b', question_lower):
                return True
        
        return False
    
    def is_likely_diagnosis_question(self, question: str) -> bool:
        """
        Improved diagnosis detection
        
        Args:
            question: Question text
        
        Returns:
            True if likely a diagnosis question
        """
        question_lower = question.lower()
        
        # Pattern 1: Explicit diagnosis keywords
        for keyword in self.diagnosis_keywords:
            if keyword in question_lower:
                # Check if in diagnostic context
                if any(pattern in question_lower for pattern in [
                    'does', 'is it', 'what', 'have', 'disease', 'condition'
                ]):
                    return True
        
        # Pattern 2: Short diagnosis questions
        diagnosis_patterns = [
            r'is it (\w+)',  # "Is it meningitis?"
            r'does.*have',   # "Does my child have"
            r'do i have',    # "Do I have"
            r'what disease|what condition',  # "What disease"
            r'diagnose|diagnosis',  # "Can you diagnose"
        ]
        
        for pattern in diagnosis_patterns:
            if re.search(pattern, question_lower):
                return True
        
        return False
    
    def extract_drug_names_improved(self, question: str) -> List[str]:
        """
        Improved drug extraction that finds all drugs
        
        Args:
            question: Question text
        
        Returns:
            List of found drugs
        """
        drugs = []
        question_lower = question.lower()
        
        # Extended drug list
        all_drugs = {
            'ibuprofen': ['ibuprofen', 'ibprofen', 'advil', 'motrin'],
            'paracetamol': ['paracetamol', 'acetaminophen', 'tylenol'],
            'aspirin': ['aspirin'],
            'naproxen': ['naproxen', 'naprosyn'],
            'penicillin': ['penicillin', 'pencillin'],
            'amoxicillin': ['amoxicillin', 'amoxcilin'],
            'azithromycin': ['azithromycin', 'zithromax'],
            'cephalexin': ['cephalexin', 'cefalexin'],
        }
        
        for canonical, variants in all_drugs.items():
            for variant in variants:
                # Find word boundaries to avoid partial matches
                if re.search(rf'\b{re.escape(variant)}\b', question_lower):
                    if canonical not in drugs:
                        drugs.append(canonical)
                    break
        
        return drugs
    
    def classify_intent_improved(self, question: str) -> Tuple[str, float]:
        """
        Improved intent classification with better handling
        
        Args:
            question: Question text
        
        Returns:
            Tuple of (intent, confidence)
        """
        question_lower = question.lower()
        
        # IMPROVEMENT: Check for diagnosis first (safety-critical)
        if self.is_likely_diagnosis_question(question):
            # This is a diagnosis attempt - mark for safety filter
            return ('DIAGNOSIS_QUESTION', 0.85)
        
        # IMPROVEMENT: Check for negation context
        has_negation = self.detect_negation(question)
        
        # Check each intent pattern
        best_match = None
        best_score = 0.0
        
        for intent, patterns in self.improved_patterns.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    matches += 1
            
            if matches > 0:
                # Calculate confidence
                confidence = min(0.95, 0.70 + (matches * 0.10))
                
                if confidence > best_score:
                    best_score = confidence
                    best_match = intent
        
        # Default fallback
        if best_match is None:
            return ('MEDICATION_INFO', 0.30)
        
        return (best_match, best_score)
    
    def detect_negation(self, query: str) -> bool:
        """
        Detect negation words in query to avoid misinterpretation
        E.g., "NOT allergic", "no side effects", "never had problems"
        Returns: True if negation detected, False otherwise
        """
        query_lower = query.lower()
        negation_patterns = [
            r'\bnot\b', r'\bno\b', r'\bnever\b', r"\bn't\b",
            r'\bwithout\b', r'\bnone\b', r'\bneither\b'
        ]
        
        for pattern in negation_patterns:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def process_query_improved(self, question: str, patient_id: Optional[str] = None) -> Dict:
        """
        Process query with improved logic
        
        Args:
            question: User question
            patient_id: Patient ID for context
        
        Returns:
            Processing result dict
        """
        # Normalize
        normalized = self.normalize_question(question)
        
        # Extract drugs
        drugs = self.extract_drug_names_improved(question)
        
        # Extract context
        context = self.extract_patient_context(question)
        
        # Extract symptoms
        symptoms = self.extract_symptom_context(question)
        
        # Classify intent (improved)
        intent, confidence = self.classify_intent_improved(normalized)
        
        # Check for negation
        has_negation = self.detect_negation(question)
        
        result = {
            'original_question': question,
            'normalized': normalized,
            'intent': intent,
            'confidence': confidence,
            'drug_names': drugs,
            'patient_context': context,
            'symptoms': symptoms,
            'has_negation': has_negation,
            'processed': True,
        }
        
        logger.info(
            f"[QUERY_PROCESSOR] Processed: intent={intent} ({confidence:.2f}), "
            f"drugs={drugs}, negation={has_negation}"
        )
        
        return result


# Test the improvements
if __name__ == "__main__":
    processor = ImprovedPatientQueryProcessor()
    
    test_cases = [
        "Is it meningitis?",
        "What disease?",
        "My child is NOT allergic to anything",
        "Tell me about ibuprofen, aspirin, and naproxen",
        "Can I give both paracetamol and ibuprofen?",
    ]
    
    for question in test_cases:
        result = processor.process_query_improved(question)
        print(f"\nQuestion: {question}")
        print(f"Intent: {result['intent']} ({result['confidence']:.2f})")
        print(f"Drugs: {result['drug_names']}")
        print(f"Negation: {result['has_negation']}")
