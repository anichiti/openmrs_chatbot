"""
Patient Safety Filter
Prevents patient/parent questions that shouldn't be answered and adds safety disclaimers

Blocks:
- Prescription/dosing requests
- Diagnosis questions
- Out-of-scope medical queries
- Direct medical advice requests

Allows:
- General medication information
- Symptom education
- Safety/allergy information
- When to see a doctor guidance
"""

import re
from typing import Dict, Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PatientSafetyFilter:
    """Filter and validate patient/parent medication queries for safety"""
    
    def __init__(self):
        """Initialize safety patterns and messaging"""
        
        # DANGEROUS: Prescription/Dosing Requests
        self.prescription_patterns = [
            r'what.*dose',
            r'how.*dose',
            r'how.*many.*mg',
            r'how.*many.*tablet',
            r'how.*many.*capsule',
            r'how.*much',
            r'dosage.*how',
            r'dose.*how',
            r'how.*give',
            r'how.*often',
            r'frequency',
            r'should.*give',
            r'should.*prescribe',
            r'can.*prescribe',
            r'can.*administer',
            r'recommendation.*dose',
        ]
        
        # DANGEROUS: Diagnosis Questions
        self.diagnosis_patterns = [
            # Full phrases
            r'does.*have.*disease|does.*have.*condition|does.*have.*asthma|does.*have.*fever|does.*have.*diabetes',
            # Short phrases
            r'is it.*(?:disease|condition|asthma|diabetes|meningitis|pneumonia|flu|infection)',
            # Generic diagnosis
            r'what.*disease|what.*condition|what.*illness',
            r'diagnose|diagnosis|is.*sick|is.*ill',
            # Can you/do you identify
            r'can.*diagnose|can.*identify.*disease|do you.*recognize',
        ]
        
        # DANGEROUS: Out-of-Scope Medical Advice
        self.out_of_scope_patterns = [
            r'cure for',
            r'treatment.*cancer',
            r'specialist.*recommend',
            r'surgery',
            r'hospital',
            r'emergency.*treatment',
            r'rare.*disease',
            r'genetic.*condition',
            r'mental.*health',
            r'psychiatric',
        ]
        
        # SAFE: Educational Information (Can Answer)
        self.safe_patterns = [
            r'what.*is.*medic',
            r'tell me.*about',
            r'how does.*work',
            r'what.*used for',
            r'side effect',
            r'when.*see.*doctor',
            r'tell doctor',
            r'before.*start',
            r'monitoring',
            r'allergic.*sign',
        ]
        
        # Safety warning templates
        self.safety_messages = {
            'prescription_request': (
                "[SAFETY WARNING] I cannot recommend doses or prescriptions.\n\n"
                "Only a doctor or pharmacist can recommend:\n"
                "  - How much medicine to give\n"
                "  - How often to give it\n"
                "  - Duration of treatment\n\n"
                "ACTION: Consult your healthcare provider or pharmacist."
            ),
            
            'diagnosis_request': (
                "[SAFETY WARNING] I am not a diagnostic tool.\n\n"
                "I cannot diagnose medical conditions. Only a healthcare professional can:\n"
                "  - Examine your child\n"
                "  - Run tests if needed\n"
                "  - Make a diagnosis\n\n"
                "ACTION: See a doctor for medical evaluation."
            ),
            
            'out_of_scope': (
                "[SAFETY WARNING] This question is beyond my knowledge base.\n\n"
                "I am designed for basic medication questions about:\n"
                "  - Current medications\n"
                "  - Allergy safety\n"
                "  - General medication information\n\n"
                "For specialized medical conditions, please consult:\n"
                "  - Your healthcare provider\n"
                "  - A medical specialist\n"
                "  - Your local clinic or hospital"
            ),
            
            'allergy_warning': (
                "[ALERT] Allergy or contraindication detected.\n\n"
                "IMPORTANT: Before giving any medication, discuss with your doctor:\n"
                "  - Known allergies\n"
                "  - Current medications\n"
                "  - Any medical conditions\n\n"
                "Your pharmacist can also check for drug interactions."
            ),
            
            'patient_restricted': (
                "[INFORMATION] This information requires medical guidance.\n\n"
                "While I can provide general information, your doctor or pharmacist "
                "should make the final recommendation based on your child's:\n"
                "  - Age and weight\n"
                "  - Medical history\n"
                "  - Current health status"
            ),
        }
    
    def check_prescription_request(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Check if question is asking for prescription/dosing advice
        
        Args:
            question: Normalized question text
        
        Returns:
            Tuple of (is_prescription_request: bool, warning_message: str or None)
        """
        question_lower = question.lower()
        
        for pattern in self.prescription_patterns:
            if re.search(pattern, question_lower):
                logger.warning(f"[SAFETY] Detected prescription request: {question}")
                return (True, self.safety_messages['prescription_request'])
        
        return (False, None)
    
    def check_diagnosis_request(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Check if question is asking for diagnosis
        
        Args:
            question: Normalized question text
        
        Returns:
            Tuple of (is_diagnosis_request: bool, warning_message: str or None)
        """
        question_lower = question.lower()
        
        for pattern in self.diagnosis_patterns:
            if re.search(pattern, question_lower):
                logger.warning(f"[SAFETY] Detected diagnosis request: {question}")
                return (True, self.safety_messages['diagnosis_request'])
        
        return (False, None)
    
    def check_out_of_scope(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Check if question is out of scope for this chatbot
        
        Args:
            question: Normalized question text
        
        Returns:
            Tuple of (is_out_of_scope: bool, warning_message: str or None)
        """
        question_lower = question.lower()
        
        for pattern in self.out_of_scope_patterns:
            if re.search(pattern, question_lower):
                logger.warning(f"[SAFETY] Detected out-of-scope question: {question}")
                return (True, self.safety_messages['out_of_scope'])
        
        return (False, None)
    
    def is_safe_to_answer(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if it's safe to answer this patient question
        
        Args:
            question: Normalized question text
        
        Returns:
            Tuple of (safe_to_answer: bool, warning_message_if_unsafe: str or None)
        """
        # First check all dangerous patterns
        is_rx, rx_msg = self.check_prescription_request(question)
        if is_rx:
            return (False, rx_msg)
        
        is_dx, dx_msg = self.check_diagnosis_request(question)
        if is_dx:
            return (False, dx_msg)
        
        is_oos, oos_msg = self.check_out_of_scope(question)
        if is_oos:
            return (False, oos_msg)
        
        # If no dangerous patterns, safe to answer
        return (True, None)
    
    def validate_response_for_patient(self, response: str, drug_name: Optional[str] = None) -> Dict:
        """
        Validate that a response is patient-safe before sending
        
        Args:
            response: Generated response text
            drug_name: Drug name if medication-related
        
        Returns:
            Dict with:
            - is_safe: bool
            - warnings: list of warnings to add
            - final_response: response with safety additions
        """
        warnings = []
        final_response = response
        
        # Check if response mentions dosing or prescribing
        if re.search(r'dose|dosage|mg|tablet|capsule', response.lower()):
            warnings.append(
                "\n\n[REMINDER] Your doctor or pharmacist should confirm "
                "the appropriate dose for your child's age and weight."
            )
        
        # Check if response might be medical advice
        if re.search(r'should|must|need to|have to', response.lower()):
            warnings.append(
                "\n\n[REMINDER] This is educational information only. "
                "Always consult your healthcare provider before starting any medication."
            )
        
        # Add allergy warning if applicable
        if drug_name:
            warnings.append(
                f"\n\n[SAFETY CHECK] Before giving {drug_name}, tell your doctor about:\n"
                "  - Any known allergies\n"
                "  - Other medications your child is taking\n"
                "  - Any medical conditions"
            )
        
        # Combine warnings
        if warnings:
            final_response = response + "".join(warnings)
        
        return {
            'is_safe': len(warnings) == 0,
            'warnings': warnings,
            'final_response': final_response
        }
    
    def assess_question_safety(self, question: str, intent: str) -> Dict:
        """
        Complete safety assessment of a patient question
        
        Args:
            question: Normalized question text
            intent: Query intent from processor
        
        Returns:
            Dict with:
            - safe: bool (safe to process)
            - blocked: bool (dangerous pattern detected)
            - block_reason: str (reason if blocked)
            - intent: str (original intent)
            - severity: str (low/medium/high safety risk)
            - recommendations: list (what to do)
        """
        safe, warning = self.is_safe_to_answer(question)
        
        result = {
            'safe': safe,
            'blocked': not safe,
            'block_reason': warning if not safe else None,
            'original_question': question,
            'intent': intent,
            'severity': 'none' if safe else 'high',
            'recommendations': []
        }
        
        # Add recommendations for blocked questions
        if not safe:
            if 'dose' in warning.lower() or 'prescribe' in warning.lower():
                result['recommendations'] = [
                    'Redirect to: "Please ask your doctor or pharmacist"',
                    'Offer: "I can provide general information about the medication"'
                ]
                result['severity'] = 'high'
            
            elif 'diagnose' in warning.lower():
                result['recommendations'] = [
                    'Redirect to: "Only a doctor can diagnose"',
                    'Offer: "I can provide information about symptoms"'
                ]
                result['severity'] = 'high'
            
            elif 'scope' in warning.lower():
                result['recommendations'] = [
                    'Redirect to: Healthcare provider, specialist, or clinic',
                    'Explain: This is specialized knowledge beyond my database'
                ]
                result['severity'] = 'medium'
        
        logger.info(
            f"[SAFETY_FILTER] Question assessment: "
            f"safe={safe}, severity={result['severity']}, intent={intent}"
        )
        
        return result
    
    def filter_patient_query(self, question: str, intent: str) -> Dict:
        """
        Complete safety filtering pipeline for patient query
        
        Args:
            question: Normalized question
            intent: Query intent from processor
        
        Returns:
            Dict with:
            - should_answer: bool (safe to proceed)
            - block_message: str (if blocked)
            - processing_allowed: bool
            - safety_level: str
        """
        assessment = self.assess_question_safety(question, intent)
        
        return {
            'should_answer': assessment['safe'],
            'block_message': assessment['block_reason'],
            'processing_allowed': assessment['safe'],
            'safety_level': assessment['severity'],
            'intent': assessment['intent'],
            'recommendations': assessment['recommendations']
        }
