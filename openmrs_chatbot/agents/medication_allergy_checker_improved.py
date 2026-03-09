"""
Improved Medication-Allergy Checker
Fix: Only block prescribing recommendations, not educational questions about patient's allergies
"""

from typing import Dict, List, Tuple, Optional

class ImprovedMedicationAllergyChecker:
    """
    Only checks allergies in prescribing context, not educational context
    """
    
    def __init__(self):
        """Initialize with drug class mappings"""
        self.drug_classes = {
            'PENICILLINS': ['penicillin', 'amoxicillin', 'ampicillin'],
            'CEPHALOSPORINS': ['cephalexin', 'cefalexin', 'ceftriaxone'],
            'NSAIDS': ['ibuprofen', 'naproxen', 'aspirin', 'indomethacin'],
            'ACETAMINOPHEN': ['acetaminophen', 'paracetamol', 'tylenol'],
            'MACROLIDES': ['erythromycin', 'azithromycin', 'clarithromycin'],
            'FLUOROQUINOLONES': ['ciprofloxacin', 'levofloxacin', 'norfloxacin'],
        }
        
        self.cross_reactivity = {
            'PENICILLINS': ['CEPHALOSPORINS'],
            'CEPHALOSPORINS': ['PENICILLINS'],
        }
    
    def check_allergy_for_prescription(
        self,
        drug_name: str,
        patient_allergies: List[Dict[str, str]],
        intent: str
    ) -> Dict:
        """
        Check allergy ONLY when prescribing, not for educational questions
        
        Args:
            drug_name: Drug to prescribe
            patient_allergies: List of patient allergies
            intent: Question intent (safety-critical for decision)
        
        Returns:
            Allergy check result
        """
        result = {
            'safe': True,
            'conflict': False,
            'drug': drug_name,
            'severity': 'None',
            'message': '',
            'should_check': False  # NEW: Flag for whether allergy matters
        }
        
        # IMPROVEMENT: Only check allergies for prescribing intents
        # These intents mean "I want to give this drug"
        prescribing_intents = ['MEDICATION_DOSE', 'MEDICATION_PRESCRIBE']
        
        # Do NOT check for educational intents like MEDICATION_INFO,
        # MEDICATION_ALLERGY_CHECK (checking education), etc.
        
        if intent not in prescribing_intents:
            result['should_check'] = False
            result['message'] = "Educational question - allergy check not needed"
            return result
        
        result['should_check'] = True
        
        # Only now check if drug is contraindicated
        drug_lower = drug_name.lower().strip()
        drug_class = self._get_drug_class(drug_name)
        
        for allergy in patient_allergies:
            # Support both 'medication' and 'drug_name' keys for flexibility
            allergy_med = (allergy.get('medication') or allergy.get('drug_name', '')).lower().strip()
            allergy_severity = allergy.get('severity', 'Mild')
            
            # Direct match
            if allergy_med == drug_lower:
                result['safe'] = False
                result['conflict'] = True
                result['severity'] = allergy_severity
                result['message'] = f"CONTRAINDICATED: Patient allergic to {drug_name}"
                return result
            
            # Drug class match
            if drug_class:
                allergy_class = self._get_drug_class(allergy_med)
                if allergy_class and allergy_class == drug_class:
                    result['safe'] = False
                    result['conflict'] = True
                    result['severity'] = allergy_severity
                    result['message'] = f"CLASS ALLERGY: {allergy_med} ({allergy_class}), {drug_name} is same class"
                    return result
            
            # Cross-reactivity
            if drug_class in self.cross_reactivity:
                for cross_class in self.cross_reactivity[drug_class]:
                    allergy_class = self._get_drug_class(allergy_med)
                    if allergy_class == cross_class:
                        result['safe'] = False
                        result['conflict'] = True
                        result['severity'] = allergy_severity
                        result['message'] = f"CROSS-REACTIVITY: {drug_name} has cross-reactivity with {allergy_med}"
                        return result
        
        result['message'] = f"Safe: No contraindications to {drug_name}"
        return result
    
    def _get_drug_class(self, drug_name: str) -> Optional[str]:
        """Get drug class"""
        drug_lower = drug_name.lower()
        for drug_class, drugs in self.drug_classes.items():
            if drug_lower in [d.lower() for d in drugs]:
                return drug_class
        return None


# Usage recommendations
print("""
IMPROVEMENT SUMMARY:
====================

OLD BEHAVIOR (Over-Blocking):
  Patient allergic to ibuprofen
  Q: "Tell me about ibuprofen" (intent=MEDICATION_INFO)
  Result: BLOCKED - Wrong! This is educational

NEW BEHAVIOR (Correct):
  Patient allergic to ibuprofen
  Q: "Tell me about ibuprofen" (intent=MEDICATION_INFO)
  Result: ALLOWED - Correct! Only educational
  
  Q: "Can you prescribe ibuprofen?" (intent=MEDICATION_DOSE)
  Result: BLOCKED - Correct! This would prescribe a contraindicated drug

KEY CHANGE:
- Added intent parameter to allergy check
- Only blocks when intent is prescribing-related
- Allows educational questions about patient's own allergies

INTENTS THAT TRIGGER ALLERGY CHECKS:
- MEDICATION_DOSE (dose requests)  
- MEDICATION_PRESCRIBE (prescription requests)

INTENTS THAT DO NOT TRIGGER ALLERGY CHECKS:
- MEDICATION_INFO (asking about medication)
- MEDICATION_ALLERGY_CHECK (asking about allergies)
- MEDICATION_LIST (listing current meds)
- MEDICATION_SAFETY_CHECK (general safety info)
- MEDICATION_INTERACTION (interaction questions)
""")
