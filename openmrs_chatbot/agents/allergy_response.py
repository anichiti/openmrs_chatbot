"""
Allergy Response Formatters for Doctor and Patient Modes
"""

from utils.logger import setup_logger

logger = setup_logger(__name__)


class AllergyResponseDoctor:
    """Format allergy information for doctors"""
    
    @staticmethod
    def format_drug_allergy_check(drug_name, allergy_check_result, patient_id, patient_name=None):
        """
        Format drug allergy check result for doctor
        
        Args:
            drug_name: Drug being checked
            allergy_check_result: Result from check_drug_allergy()
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted report string
        """
        report = f"DRUG ALLERGY CHECK - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        
        report += f"\n{'='*70}\n"
        report += f"Drug Being Considered: {drug_name}\n"
        report += f"{'='*70}\n\n"
        
        if allergy_check_result['is_contraindicated']:
            report += "[ALERT] CONTRAINDICATED\n"
            report += f"Matched Allergen: {allergy_check_result['allergen_matched']}\n"
            report += f"Severity: {allergy_check_result['severity']}\n"
            report += f"\n{allergy_check_result['message']}\n\n"
            report += "RECOMMENDATION: DO NOT PRESCRIBE this drug\n"
            report += "Consider alternative medications from different drug classes\n"
        else:
            report += "[OK] SAFE TO PRESCRIBE\n"
            report += f"\n{allergy_check_result['message']}\n"
        
        report += f"\n{'='*70}\n"
        report += "Clinical Safety Notes:\n"
        report += "  - Always verify with full patient allergy history\n"
        report += "  - Review cross-reactivity risk for related drugs\n"
        report += "  - Document all allergy considerations in patient record\n"
        report += "  - Counsel patient on signs of allergic reaction\n\n"
        report += "Source: OpenMRS Patient Allergy Record\n"
        
        return report
    
    @staticmethod
    def format_patient_allergies(allergies_by_type, patient_id, patient_name=None):
        """
        Format all patient allergies for doctor
        
        Args:
            allergies_by_type: Dict with allergen_type -> [allergens] mapping
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted allergy report string
        """
        report = f"ALLERGY PROFILE - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        
        report += f"\n{'='*70}\n"
        
        if not allergies_by_type:
            report += "No documented allergies on record.\n"
        else:
            total_allergies = sum(len(v) for v in allergies_by_type.values())
            report += f"Total Documented Allergies: {total_allergies}\n"
            report += f"{'='*70}\n\n"
            
            for allergen_type, allergens in allergies_by_type.items():
                report += f"\n[{allergen_type.upper()} ALLERGIES]\n"
                report += "-" * 70 + "\n"
                
                for allergen in allergens:
                    report += f"\nAllergen: {allergen['name']}\n"
                    if allergen['severity']:
                        report += f"  Severity: {allergen['severity']}\n"
                    if allergen['comments']:
                        report += f"  Notes: {allergen['comments']}\n"
                    report += f"  Recorded: {allergen['date_recorded']}\n"
        
        report += f"\n{'='*70}\n"
        report += "Clinical Recommendations:\n"
        report += "  - Review when prescribing medications\n"
        report += "  - Assess cross-reactivity with related compounds\n"
        report += "  - Consider immunological testing if unclear\n"
        report += "  - Update records with any new allergic reactions\n\n"
        report += "Source: OpenMRS Patient Record\n"
        
        return report
    
    @staticmethod
    def format_allergy_by_type(allergy_type, allergies_by_type, patient_id, patient_name=None):
        """
        Format allergies for a specific allergy type (FOOD, DRUG, ENVIRONMENT) - Clinical version for doctors
        Filters to show only the requested allergy type with clinical detail
        
        Args:
            allergy_type: Type of allergy to show (FOOD, DRUG, ENVIRONMENT)
            allergies_by_type: Dict with allergen_type -> [allergens] mapping
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted clinical allergy report for the specific type
        """
        report = f"ALLERGY PROFILE - {allergy_type.upper()} ALLERGIES - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        
        report += f"\n{'='*70}\n"
        
        # Check if this allergy type is documented
        if allergy_type.upper() not in allergies_by_type or not allergies_by_type[allergy_type.upper()]:
            report += f"No documented {allergy_type.lower()} allergies on record.\n"
            report += f"\n{'='*70}\n"
            report += "Clinical Notes:\n"
            report += f"  - Patient reports no {allergy_type.lower()} allergies\n"
            report += f"  - Continue to monitor and document any new {allergy_type.lower()} allergies\n"
        else:
            allergens = allergies_by_type[allergy_type.upper()]
            report += f"Total {allergy_type.upper()} ALLERGIES: {len(allergens)}\n"
            report += f"{'='*70}\n\n"
            
            for i, allergen in enumerate(allergens, 1):
                report += f"{i}. Allergen: {allergen['name']}\n"
                if allergen['severity']:
                    report += f"   Severity: {allergen['severity']}\n"
                if allergen['comments']:
                    report += f"   Notes: {allergen['comments']}\n"
                report += f"   Recorded: {allergen['date_recorded']}\n\n"
            
            report += f"{'='*70}\n"
            report += f"Clinical Recommendations ({allergy_type.upper()}):\n"
            
            if allergy_type.upper() == 'DRUG':
                report += "  - Review when prescribing medications\n"
                report += "  - Assess cross-reactivity with related compounds\n"
                report += "  - Consider immunological testing if severity unclear\n"
                report += "  - Document all drug allergy considerations in patient record\n"
                report += "  - Use alternative drug classes when available\n"
            elif allergy_type.upper() == 'FOOD':
                report += "  - Consider nutritional alternatives\n"
                report += "  - Counsel patient/caregiver on food avoidance\n"
                report += "  - Assess for cross-reactivity with similar foods\n"
                report += "  - Consider allergy testing if severity unclear\n"
            elif allergy_type.upper() == 'ENVIRONMENT':
                report += "  - Assess environmental exposure opportunities\n"
                report += "  - Consider preventive measures (antihistamines, avoidance)\n"
                report += "  - Monitor for seasonal variation in symptoms\n"
                report += "  - Consider immunotherapy if indicated\n"
        
        report += "\nSource: OpenMRS Patient Record\n"
        
        return report

class AllergyResponsePatient:
    """Format allergy information for patients - simplified, patient-friendly"""
    
    @staticmethod
    def format_drug_allergy_check(drug_name, allergy_check_result, patient_id, patient_name=None):
        """
        Format drug allergy check result for patient (simple, non-clinical language)
        
        Args:
            drug_name: Drug being checked
            allergy_check_result: Result from check_drug_allergy()
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted report string (patient-friendly)
        """
        report = f"MEDICATION CHECK - {drug_name.upper()}\n"
        report += f"{'='*70}\n\n"
        
        if allergy_check_result['is_contraindicated']:
            report += "[⚠️  WARNING] You have an allergy to this medication!\n\n"
            report += f"Allergy: {allergy_check_result['allergen_matched']}\n"
            report += f"Severity: {allergy_check_result['severity']}\n\n"
            report += f"{allergy_check_result['message']}\n\n"
            report += "ACTION: Do NOT take this medication\n"
            report += "NEXT STEP: Consult your doctor for alternative medication options\n"
        else:
            report += "[✓] No documented allergy to this medication\n\n"
            report += f"{allergy_check_result['message']}\n\n"
            report += "REMINDER: Always follow your doctor's instructions and dosage recommendations\n"
        
        report += f"\n{'='*70}\n"
        report += "If you experience any allergic symptoms (rash, swelling, breathing\n"
        report += "difficulty), stop taking the medication and seek medical help immediately.\n\n"
        report += "Source: Your Medical Records\n"
        
        return report
    
    @staticmethod
    def format_patient_allergies(allergies_by_type, patient_id, patient_name=None):
        """
        Format all patient allergies for patient viewing (simple language)
        
        Args:
            allergies_by_type: Dict with allergen_type -> [allergens] mapping
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted allergy report string (patient-friendly)
        """
        report = f"YOUR ALLERGIES\n"
        report += f"{'='*70}\n\n"
        
        if not allergies_by_type:
            report += "✓ No documented allergies on your medical record.\n\n"
            report += "If you discover a new allergy, tell your doctor immediately.\n"
        else:
            total_allergies = sum(len(v) for v in allergies_by_type.values())
            if total_allergies == 1:
                report += f"You have 1 documented allergy:\n\n"
            else:
                report += f"You have {total_allergies} documented allergies:\n\n"
            
            for allergen_type, allergens in allergies_by_type.items():
                report += f"{allergen_type.upper() if allergen_type != 'DRUG' else 'Medications'}:\n"
                report += "-" * 70 + "\n"
                
                for allergen in allergens:
                    report += f"\n• {allergen['name']}"
                    if allergen['severity']:
                        report += f" (Severity: {allergen['severity']})"
                    report += "\n"
                    if allergen['comments']:
                        report += f"  Note: {allergen['comments']}\n"
                
                report += "\n"
        
        report += f"{'='*70}\n"
        report += "IMPORTANT REMINDERS:\n"
        report += "  • Carry your allergy information with you at all times\n"
        report += "  • Tell every doctor/pharmacist about your allergies\n"
        report += "  • Watch for allergic reactions after taking new medications\n"
        report += "  • Report any new allergies to your doctor\n"
        report += "  • In emergency situations, mention your allergies immediately\n\n"
        report += "Questions? Consult your doctor or pharmacist.\n"
        report += "Source: Your Medical Records\n"
        
        return report
    
    @staticmethod
    def format_drug_allergies_only(allergies_by_type, patient_id, patient_name=None, asking_about_self=True):
        """
        Format ONLY drug allergies for patient (filters out environment/food allergies)
        Used when patient asks specifically about medicine allergies
        
        Args:
            allergies_by_type: Dict with allergen_type -> [allergens] mapping
            patient_id: Patient external ID  
            patient_name: Patient name (optional)
            asking_about_self: Whether asking about self (True) or child (False)
        
        Returns:
            Formatted drug allergy report string (patient-friendly)
        """
        # Determine pronouns based on who is being asked about (DYNAMIC - NOT HARDCODED)
        if asking_about_self:
            subject_singular = "You have 1 documented"
            subject_plural = "You have {} documented"
            can_safely = "You can safely"
        else:
            subject_singular = "Your child has 1 documented"
            subject_plural = "Your child has {} documented"
            can_safely = "Your child can safely"
        
        report = f"MEDICINE ALLERGIES\n"
        report += f"{'='*70}\n\n"
        
        # Extract only drug allergies
        drug_allergies = allergies_by_type.get('DRUG', [])
        
        if not drug_allergies:
            report += "✓ No documented medicine allergies on your medical record.\n\n"
            report += f"{can_safely} use most medicines unless otherwise advised.\n"
        else:
            if len(drug_allergies) == 1:
                report += f"{subject_singular} medicine allergy:\n\n"
            else:
                report += f"{subject_plural.format(len(drug_allergies))} medicine allergies:\n\n"
            
            for allergen in drug_allergies:
                report += f"• {allergen['name']}"
                if allergen['severity']:
                    report += f" (Severity: {allergen['severity']})"
                report += "\n"
                if allergen['comments']:
                    report += f"  Note: {allergen['comments']}\n"
            
            report += "\n"
            report += f"{'='*70}\n"
            report += "IMPORTANT:\n"
            report += "  • Tell every doctor and pharmacist about these allergies\n"
            report += "  • Ask your pharmacist about alternative medicines\n"
            report += "  • Watch for allergic reactions (rash, swelling, difficulty breathing)\n"
            report += "  • Seek immediate help if allergic reaction occurs\n\n"
        
        report += "Questions? Consult your doctor or pharmacist.\n"
        report += "Source: Your Medical Records\n"
        
        return report
    
    @staticmethod
    def detect_allergy_type_from_question(user_question):
        """
        Analyze patient's question to detect what allergy type they're asking about
        
        Args:
            user_question: Patient's question string
        
        Returns:
            Tuple: (allergy_type, keywords_found)
            - 'FOOD' for food/nut/allergy questions
            - 'DRUG' for medication/medicine/drug questions  
            - 'ENVIRONMENT' for environmental/pollen/dust questions
            - 'GENERAL' if unclear (default to all allergies)
        """
        question_lower = user_question.lower()
        
        # Food allergy keywords
        food_keywords = ['food', 'nut', 'nuts', 'peanut', 'dairy', 'egg', 'eggs', 'shellfish', 
                        'seafood', 'fish', 'gluten', 'wheat', 'milk', 'eat', 'eating', 'eaten']
        
        # Drug allergy keywords
        drug_keywords = ['medicine', 'medication', 'medicin', 'drug', 'drugs', 'tablet', 
                        'inject', 'injection', 'antibiotic', 'prescrib']
        
        # Environment allergy keywords
        environment_keywords = ['pollen', 'dust', 'pet', 'pets', 'animal', 'bee', 'insect', 
                              'environmental', 'seasonal', 'grass', 'tree', 'mold']
        
        # Check for food allergies
        food_found = sum(1 for kw in food_keywords if kw in question_lower)
        
        # Check for drug allergies
        drug_found = sum(1 for kw in drug_keywords if kw in question_lower)
        
        # Check for environment allergies
        env_found = sum(1 for kw in environment_keywords if kw in question_lower)
        
        # Determine primary allergy type based on keyword matches
        if food_found > 0 and food_found >= drug_found and food_found >= env_found:
            return 'FOOD', food_found
        elif drug_found > 0 and drug_found >= food_found and drug_found >= env_found:
            return 'DRUG', drug_found
        elif env_found > 0 and env_found >= food_found and env_found >= drug_found:
            return 'ENVIRONMENT', env_found
        else:
            return 'GENERAL', 0
    
    @staticmethod
    def detect_asking_about_self(user_question):
        """
        Detect if user is asking about themselves or about someone else (child, dependent)
        
        Args:
            user_question: Patient's question string
        
        Returns:
            Boolean: True if asking about self, False if asking about child/dependent
        """
        question_lower = user_question.lower()
        
        # Child/family reference keywords (check these FIRST - they're more specific)
        child_keywords = ['my child', 'my children', 'my kid', 'my kids', 'my baby', 
                         'my son', 'my daughter', 'my family', 'my dependent', 'they have',
                         'their ', 'our child', 'our children']
        
        # Self-reference keywords (more general)
        self_keywords = ['i have', 'do i', 'am i', 'will i', 'can i', 'do i have',
                        'myself', 'i\'m allergic', 'i\'m', 'about me', 'about myself']
        
        # Count child references (check for these first as they're more specific)
        child_count = sum(1 for kw in child_keywords if kw in question_lower)
        
        # Count self references
        self_count = sum(1 for kw in self_keywords if kw in question_lower)
        
        # If any child keywords found, assume asking about child
        if child_count > 0:
            return False
        
        # If any self keywords found, assume asking about self
        if self_count > 0:
            return True
        
        # Default: assume asking about self if unclear
        return True
    
    @staticmethod
    def format_allergy_by_type(allergy_type, allergies_by_type, patient_id, patient_name=None, asking_about_self=True):
        """
        Format allergies for a specific allergy type (FOOD, DRUG, ENVIRONMENT)
        NOW GENERALIZED for any patient age/relationship
        
        Args:
            allergy_type: Type of allergy to show (FOOD, DRUG, ENVIRONMENT)
            allergies_by_type: Dict with allergen_type -> [allergens] mapping
            patient_id: Patient external ID
            patient_name: Patient name (optional)
            asking_about_self: Whether asking about self (True) or child (False)
        
        Returns:
            Formatted allergy report string specific to the allergy type
        """
        # Determine pronoun based on who is being asked about
        if asking_about_self:
            subject_singular = "You have 1 documented"
            subject_plural = "You have {} documented"
            subject_none = "You have no documented"
            can_safely = "You can safely"
        else:
            subject_singular = "Your child has 1 documented"
            subject_plural = "Your child has {} documented"
            subject_none = "Your child has no documented"
            can_safely = "Your child can safely"
        
        # Map allergy type to display name and reassurance message
        type_config = {
            'FOOD': {
                'header': 'FOOD ALLERGIES',
                'singular': f'{subject_singular} food allergy',
                'plural': f'{subject_plural} food allergies',
                'none_message': f'{subject_none} food allergies on your medical record.',
                'reassurance': f'{can_safely} eat most common foods unless otherwise advised.',
                'reminder': [
                    '  • Always check food ingredients before eating',
                    '  • Tell restaurants and food servings about food allergies',
                    '  • Watch for allergic reactions after trying new foods',
                    '  • Keep emergency medications nearby if prescribed'
                ]
            },
            'DRUG': {
                'header': 'MEDICINE ALLERGIES',
                'singular': f'{subject_singular} medicine allergy',
                'plural': f'{subject_plural} medicine allergies',
                'none_message': f'{subject_none} medicine allergies on your medical record.',
                'reassurance': f'{can_safely} use most medicines unless otherwise advised.',
                'reminder': [
                    '  • Tell every doctor and pharmacist about these allergies',
                    '  • Ask your pharmacist about alternative medicines',
                    '  • Watch for allergic reactions (rash, swelling, difficulty breathing)',
                    '  • Seek immediate help if allergic reaction occurs'
                ]
            },
            'ENVIRONMENT': {
                'header': 'ENVIRONMENTAL ALLERGIES',
                'singular': f'{subject_singular} environmental allergy',
                'plural': f'{subject_plural} environmental allergies',
                'none_message': f'{subject_none} environmental allergies on your medical record.',
                'reassurance': f'{can_safely} be exposed to most environmental triggers unless otherwise advised.',
                'reminder': [
                    '  • Avoid known allergen triggers when possible',
                    '  • Keep home clean and dust-free',
                    '  • Monitor for allergic symptoms during allergy season',
                    '  • Keep prescribed allergy medications on hand'
                ]
            }
        }
        
        # Get configuration for this allergy type
        config = type_config.get(allergy_type, type_config['DRUG'])
        
        # Add patient name personalization if available
        header = config['header']
        if patient_name:
            header = f"{patient_name.split()[0]}'s {header.lower()}"
            header = header.replace("'s food", "'s Food").replace("'s medicine", "'s Medicine").replace("'s environmental", "'s Environmental")
        
        report = f"{header}\n"
        report += f"{'='*70}\n\n"
        
        # Extract allergies of this type
        type_allergies = allergies_by_type.get(allergy_type, [])
        
        if not type_allergies:
            report += f"✓ {config['none_message']}\n\n"
            report += f"{config['reassurance']}\n"
        else:
            if len(type_allergies) == 1:
                report += f"{config['singular']}:\n\n"
            else:
                report += f"{config['plural'].format(len(type_allergies))}:\n\n"
            
            for allergen in type_allergies:
                report += f"• {allergen['name']}"
                if allergen['severity']:
                    report += f" (Severity: {allergen['severity']})"
                report += "\n"
                if allergen['comments']:
                    report += f"  Note: {allergen['comments']}\n"
            
            report += "\n"
            report += f"{'='*70}\n"
            report += "IMPORTANT:\n"
            for reminder in config['reminder']:
                report += f"{reminder}\n"
            report += "\n"
        
        report += "Questions? Consult your doctor or pharmacist.\n"
        report += "Source: Your Medical Records\n"
        
        return report
    
    @staticmethod
    def format_food_allergies_only(allergies_by_type, patient_id, patient_name=None):
        """
        Format ONLY food allergies for patient
        Used when patient asks specifically: "Can my child eat nuts? Do they have food allergies?"
        
        Args:
            allergies_by_type: Dict with allergen_type -> [allergens] mapping
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted food allergy report string (patient-friendly)
        """
        return AllergyResponsePatient.format_allergy_by_type(
            'FOOD', allergies_by_type, patient_id, patient_name
        )