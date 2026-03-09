"""
Medication-Allergy Checker (Phase 1C)
Cross-references patient medications with allergies to detect safety conflicts

Features:
- Check single medication against patient allergies
- Check multiple medications for interactions
- Detect drug class conflicts
- Provide severity levels (none, mild, moderate, severe)
- Generate safety alerts
- Suggest alternatives
"""

import json
from typing import Dict, List, Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MedicationAllergyChecker:
    """Check medications against patient allergies and drug interactions"""
    
    def __init__(self):
        """Initialize drug class mappings and allergy patterns"""
        
        # Drug classifications by therapeutic class
        self.drug_classes = {
            'PENICILLINS': [
                'penicillin', 'amoxicillin', 'ampicillin', 'amoxicillin-clavulanate',
                'piperacillin', 'ticarcillin', 'pencillin'  # common misspelling
            ],
            'CEPHALOSPORINS': [
                'cephalexin', 'cefalexin', 'ceftriaxone', 'cefpodoxime',
                'cefdinir', 'cefixime', 'cefotaxime', 'cephalothin'
            ],
            'AMINOGLYCOSIDES': [
                'gentamicin', 'tobramycin', 'amikacin', 'neomycin', 'streptomycin'
            ],
            'NSAIDS': [
                'ibuprofen', 'naproxen', 'aspirin', 'indomethacin',
                'ketoprofen', 'meloxicam', 'diclofenac'
            ],
            'ACETAMINOPHEN': [
                'acetaminophen', 'paracetamol', 'tylenol'
            ],
            'SULFONAMIDES': [
                'sulfamethoxazole', 'sulfisoxazole', 'sulfadiazine', 'sulfasalazine'
            ],
            'ANTICONVULSANTS': [
                'phenytoin', 'valproic_acid', 'carbamazepine', 'phenobarbital',
                'lamotrigine', 'levetiracetam'
            ],
            'ANTIMALARIALS': [
                'chloroquine', 'quinine', 'mefloquine', 'artesunate'
            ],
            'MACROLIDES': [
                'erythromycin', 'azithromycin', 'clarithromycin', 'roxithromycin'
            ],
            'FLUOROQUINOLONES': [
                'ciprofloxacin', 'levofloxacin', 'norfloxacin', 'ofloxacin'
            ],
        }
        
        # Cross-reactivity patterns (drug class to drug class)
        self.cross_reactivity = {
            'PENICILLINS': ['CEPHALOSPORINS'],  # 1-3% cross-reactivity
            'CEPHALOSPORINS': ['PENICILLINS'],
            'NSAIDS': ['ACETAMINOPHEN'],  # Can potentiate risk
            'SULFONAMIDES': [],  # Limited cross-reactivity
        }
        
        # Severity classification (for pediatric dosing/age)
        self.allergy_severity_map = {
            'None': 0,
            'Mild': 1,
            'Moderate': 2,
            'Severe': 3,
            'SEVERE': 3,
        }
    
    def get_drug_class(self, drug_name: str) -> Optional[str]:
        """
        Get drug class for a medication
        
        Args:
            drug_name: Drug name (case-insensitive)
        
        Returns:
            Drug class string or None if not found
        """
        drug_lower = drug_name.lower().strip()
        
        for drug_class, drugs in self.drug_classes.items():
            if drug_lower in [d.lower() for d in drugs]:
                return drug_class
        
        return None
    
    def check_drug_allergy(
        self,
        drug_name: str,
        patient_allergies: List[Dict[str, str]]
    ) -> Dict:
        """
        Check single drug against patient allergies
        
        Args:
            drug_name: Drug to check
            patient_allergies: List of allergy dicts with 'medication' and 'severity' keys
        
        Returns:
            Dict with:
            - safe: bool
            - conflict: bool (if drug is in allergies)
            - drug: str (normalized name)
            - drug_class: str (therapeutic class)
            - matching_allergies: list (matching allergies found)
            - severity: str (None/Mild/Moderate/Severe)
            - message: str (explanation)
        """
        drug_lower = drug_name.lower().strip()
        drug_class = self.get_drug_class(drug_name)
        
        result = {
            'drug': drug_name,
            'drug_class': drug_class,
            'safe': True,
            'conflict': False,
            'matching_allergies': [],
            'severity': 'None',
            'message': f'{drug_name} is safe - no allergies to this medication'
        }
        
        # Check direct drug allergies
        for allergy in patient_allergies:
            allergy_med = allergy.get('medication', '').lower().strip()
            allergy_severity = allergy.get('severity', 'Mild')
            
            # Direct match
            if allergy_med == drug_lower:
                result['safe'] = False
                result['conflict'] = True
                result['matching_allergies'].append(allergy_med)
                result['severity'] = allergy_severity
                result['message'] = (
                    f"[ALERT] CONTRAINDICATED - Patient is allergic to {drug_name} "
                    f"(Severity: {allergy_severity})"
                )
                logger.warning(f"[MEDICATION_ALLERGY] Direct match: {drug_name} in allergies")
                return result
            
            # Check drug class match
            if drug_class:
                allergy_class = self.get_drug_class(allergy_med)
                if allergy_class and allergy_class == drug_class:
                    result['safe'] = False
                    result['conflict'] = True
                    result['matching_allergies'].append(f"{allergy_med} (class: {allergy_class})")
                    result['severity'] = allergy_severity
                    result['message'] = (
                        f"[ALERT] Drug class allergy - Patient allergic to {allergy_med} "
                        f"({allergy_class}). {drug_name} is in same class. "
                        f"(Severity: {allergy_severity})"
                    )
                    logger.warning(
                        f"[MEDICATION_ALLERGY] Class match: {drug_class} in allergies"
                    )
                    return result
            
            # Check cross-reactivity
            if drug_class in self.cross_reactivity:
                for cross_reactive_class in self.cross_reactivity[drug_class]:
                    allergy_class = self.get_drug_class(allergy_med)
                    if allergy_class == cross_reactive_class:
                        result['safe'] = False
                        result['conflict'] = True
                        result['matching_allergies'].append(
                            f"{allergy_med} (cross-reactive with {drug_class})"
                        )
                        result['severity'] = allergy_severity
                        result['message'] = (
                            f"[CAUTION] Cross-reactivity risk - "
                            f"Patient allergic to {allergy_med} ({cross_reactive_class}). "
                            f"{drug_name} ({drug_class}) has known cross-reactivity. "
                            f"Use with caution. (Severity: {allergy_severity})"
                        )
                        logger.warning(
                            f"[MEDICATION_ALLERGY] Cross-reactivity: "
                            f"{drug_class} with {cross_reactive_class}"
                        )
                        return result
        
        return result
    
    def check_multiple_drugs(
        self,
        drug_names: List[str],
        patient_allergies: List[Dict[str, str]]
    ) -> Dict:
        """
        Check multiple drugs against allergies
        
        Args:
            drug_names: List of drugs to check
            patient_allergies: Patient's allergy list
        
        Returns:
            Dict with:
            - all_safe: bool
            - unsafe_drugs: list (drugs with conflicts)
            - warnings: list (warning messages)
            - results_by_drug: dict (detailed results)
        """
        results = {
            'all_safe': True,
            'unsafe_drugs': [],
            'warnings': [],
            'results_by_drug': {}
        }
        
        for drug in drug_names:
            drug_result = self.check_drug_allergy(drug, patient_allergies)
            results['results_by_drug'][drug] = drug_result
            
            if not drug_result['safe']:
                results['all_safe'] = False
                results['unsafe_drugs'].append(drug)
                results['warnings'].append(drug_result['message'])
        
        return results
    
    def check_medication_contraindications(
        self,
        current_medications: List[Dict[str, str]],
        new_drug: str,
        patient_allergies: List[Dict[str, str]]
    ) -> Dict:
        """
        Check if new drug conflicts with current medications and allergies
        
        Args:
            current_medications: List of current meds with 'name' and 'dosage' keys
            new_drug: Drug being considered
            patient_allergies: Patient's allergies
        
        Returns:
            Dict with:
            - safe_to_add: bool
            - drug: str
            - allergy_conflicts: list
            - medication_conflicts: list
            - overall_safety_message: str
        """
        result = {
            'safe_to_add': True,
            'drug': new_drug,
            'allergy_conflicts': [],
            'medication_conflicts': [],
            'overall_safety_message': f'{new_drug} can be safely considered'
        }
        
        # Check allergies first (most critical)
        allergy_check = self.check_drug_allergy(new_drug, patient_allergies)
        if not allergy_check['safe']:
            result['safe_to_add'] = False
            result['allergy_conflicts'].append(allergy_check['message'])
            result['overall_safety_message'] = (
                f"[CONTRAINDICATED] {new_drug} cannot be given: {allergy_check['message']}"
            )
            return result
        
        # Check for known interactions with current medications
        new_drug_class = self.get_drug_class(new_drug)
        current_drug_classes = [
            self.get_drug_class(med.get('name', ''))
            for med in current_medications
        ]
        
        # Add warnings for NSAID + Acetaminophen combination (risk of toxicity)
        if new_drug_class == 'NSAIDS' and 'ACETAMINOPHEN' in current_drug_classes:
            result['safe_to_add'] = False
            result['medication_conflicts'].append(
                'SIGNIFICANT CONFLICT: NSAIDs with Acetaminophen increases '
                'risk of liver/kidney toxicity'
            )
            result['overall_safety_message'] = (
                f'[CAUTION] {new_drug} (NSAID) has known interaction '
                'with currently prescribed acetaminophen'
            )
        
        if new_drug_class == 'ACETAMINOPHEN' and 'NSAIDS' in current_drug_classes:
            result['safe_to_add'] = False
            result['medication_conflicts'].append(
                'SIGNIFICANT CONFLICT: Acetaminophen with NSAIDs increases '
                'risk of liver/kidney toxicity'
            )
            result['overall_safety_message'] = (
                f'[CAUTION] {new_drug} has known interaction '
                'with currently prescribed NSAIDs'
            )
        
        return result
    
    def validate_patient_medications(
        self,
        patient_data: Dict
    ) -> Dict:
        """
        Validate all patient medications against allergies
        
        Args:
            patient_data: Dict with 'medications' and 'allergies' lists
        
        Returns:
            Dict with:
            - is_valid: bool
            - conflicts_found: int
            - safe_medications: list
            - unsafe_medications: list
            - total_alerts: int
        """
        medications = patient_data.get('medications', [])
        allergies = patient_data.get('allergies', [])
        
        result = {
            'is_valid': True,
            'conflicts_found': 0,
            'safe_medications': [],
            'unsafe_medications': [],
            'total_alerts': 0,
            'medication_status': {}
        }
        
        for med in medications:
            med_name = med.get('name', med.get('medication', '')) if isinstance(med, dict) else med
            
            check = self.check_drug_allergy(med_name, allergies)
            result['medication_status'][med_name] = check
            
            if check['safe']:
                result['safe_medications'].append(med_name)
            else:
                result['unsafe_medications'].append(med_name)
                result['is_valid'] = False
                result['conflicts_found'] += 1
                result['total_alerts'] = len(result['unsafe_medications'])
        
        return result
    
    def get_safe_alternatives(
        self,
        original_drug: str,
        patient_allergies: List[Dict[str, str]]
    ) -> Dict:
        """
        Get safe alternative drugs for given medication
        
        Args:
            original_drug: Drug to find alternatives for
            patient_allergies: Patient's known allergies
        
        Returns:
            Dict with:
            - original_drug: str
            - alternatives: list of alternative drug names
            - reasoning: str
        """
        original_class = self.get_drug_class(original_drug)
        
        if not original_class:
            return {
                'original_drug': original_drug,
                'alternatives': [],
                'reasoning': 'Drug class not found in database'
            }
        
        # Get allergy drug classes
        allergy_classes = set()
        for allergy in patient_allergies:
            allergy_drug = allergy.get('medication', '')
            allergy_class = self.get_drug_class(allergy_drug)
            if allergy_class:
                allergy_classes.add(allergy_class)
                # Add cross-reactive classes
                if allergy_class in self.cross_reactivity:
                    for cross in self.cross_reactivity[allergy_class]:
                        allergy_classes.add(cross)
        
        # Find safe alternatives from same or different classes
        alternatives = []
        
        # If patient allergic to specific drug class, suggest different class
        if original_class in allergy_classes:
            # Build alternatives based on therapeutic use
            if original_class == 'PENICILLINS':
                alternatives = ['Macrolides (azithromycin)', 'Fluoroquinolones (ciprofloxacin)']
            elif original_class == 'NSAIDS':
                alternatives = ['Acetaminophen (paracetamol)']
            elif original_class == 'CEPHALOSPORINS':
                alternatives = ['Macrolides (azithromycin)']
        
        return {
            'original_drug': original_drug,
            'original_class': original_class,
            'alternatives': alternatives if alternatives else 'Consult pharmacist for alternatives',
            'reasoning': (
                f'Patient allergic to {original_class}. '
                'Consider alternative classes (consult pharmacist)'
            )
        }
