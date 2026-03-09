"""
Medication Response Formatters for Doctor and Patient Modes
"""

from utils.logger import setup_logger

logger = setup_logger(__name__)


class MedicationResponseDoctor:
    """Format active medications for doctors"""
    
    @staticmethod
    def format_active_medications(medications, patient_id, patient_name=None):
        """
        Format active medications for doctor view
        
        Args:
            medications: List of medication dicts from OpenMRS
            patient_id: Patient external ID
            patient_name: Patient name (optional)
        
        Returns:
            Formatted medication report string
        """
        if not medications:
            return f"ACTIVE MEDICATIONS - PATIENT {patient_id}\nNo active medications found."
        
        report = f"ACTIVE MEDICATIONS REPORT - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        
        report += f"\n{'='*70}\n"
        report += f"Total Active Medications: {len(medications)}\n"
        report += f"{'='*70}\n\n"
        
        for i, med in enumerate(medications, 1):
            report += f"[MEDICATION {i}] {med['drug_name']}\n"
            report += f"  Order ID: {med['order_id']}\n"
            report += f"  Date Started: {med['date_activated']}\n"
            
            # Add indication
            indication = med.get('indication', 'Not specified')
            report += f"  Indication: {indication}\n"
            
            if med['dose']:
                dose_str = f"{med['dose']}"
                if med['dose_units']:
                    dose_str += f" {med['dose_units']}"
                report += f"  Dose: {dose_str}\n"
            
            if med['frequency']:
                report += f"  Frequency: {med['frequency']}\n"
            
            if med['instructions']:
                report += f"  Instructions: {med['instructions']}\n"
            
            if med['route']:
                report += f"  Route: {med['route']}\n"
            
            report += "\n"
        
        report += f"{'='*70}\n"
        report += "Clinical Notes:\n"
        report += "  - Review drug interactions and contraindications\n"
        report += "  - Check for duplicate therapy\n"
        report += "  - Verify dosing appropriateness\n"
        report += "  - Monitor patient compliance\n\n"
        report += "Source: OpenMRS Patient Record\n"
        
        return report


class MedicationResponsePatient:
    """Format active medications for patients"""
    
    @staticmethod
    def format_active_medications(medications, patient_name=None):
        """
        Format active medications for patient view
        
        Args:
            medications: List of medication dicts from OpenMRS
            patient_name: Patient name (optional)
        
        Returns:
            Formatted medication report string
        """
        if not medications:
            return "Your Current Medications\nYou currently have no active medications prescribed."
        
        report = "Your Current Medications\n"
        if patient_name:
            report += f"Patient: {patient_name}\n"
        
        report += f"{'='*70}\n"
        report += f"You are currently taking {len(medications)} medication(s)\n"
        report += f"{'='*70}\n\n"
        
        for i, med in enumerate(medications, 1):
            report += f"[MEDICATION {i}] {med['drug_name']}\n"
            
            # Add indication
            indication = med.get('indication', 'Not specified')
            report += f"  Indication: {indication}\n"
            
            if med['dose']:
                dose_str = f"{med['dose']}"
                if med['dose_units']:
                    dose_str += f" {med['dose_units']}"
                report += f"  Dose: {dose_str}\n"
            
            if med['instructions']:
                report += f"  Instructions: {med['instructions']}\n"
            
            report += "  Started: " + (med['date_activated'].split()[0] if med['date_activated'] else "Unknown") + "\n"
            report += "\n"
        
        report += f"{'='*70}\n"
        report += "Important - Please:\n"
        report += "  - Take medications exactly as prescribed\n"
        report += "  - Don't stop medications without consulting your doctor\n"
        report += "  - Report any side effects to your healthcare provider\n"
        report += "  - Keep all medications at room temperature\n\n"
        report += "Source: Your Medical Record\n"
        
        return report
