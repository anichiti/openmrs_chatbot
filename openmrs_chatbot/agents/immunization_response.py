"""
Immunization Response Formatters for Doctor and Patient Modes
"""

from utils.logger import setup_logger
from collections import defaultdict

logger = setup_logger(__name__)


class ImmunizationResponseFormatter:
    """Base class with shared formatting utilities"""
    
    @staticmethod
    def format_doses_by_vaccine(history):
        """
        Group immunization history by vaccine and format as dose sequence
        e.g., "DTaP: Dose 1 on 2021-01-25, Dose 2 on 2021-03-25, Dose 3 on 2021-12-25"
        
        Args:
            history: List of vaccination records with 'vaccine_name', 'dose_number', 'date_given'
        
        Returns:
            Dict with vaccine names as keys and formatted dose strings as values
        """
        vaccine_doses = defaultdict(lambda: [])
        
        for vac in history:
            vaccine_name = vac.get('vaccine_name', 'Unknown')
            dose_number = vac.get('dose_number')
            date_given = vac.get('date_given', 'Unknown')
            
            # Create dose entry
            if dose_number:
                dose_entry = f"Dose {int(dose_number)} on {date_given}"
            else:
                dose_entry = f"Given on {date_given}"
            
            vaccine_doses[vaccine_name].append({
                'dose_num': dose_number or 999,  # Sort unknown doses to end
                'text': dose_entry
            })
        
        # Sort and format each vaccine's doses
        formatted = {}
        for vaccine_name, doses in vaccine_doses.items():
            # Sort by dose number
            doses.sort(key=lambda x: x['dose_num'])
            # Join dose entries with comma
            formatted[vaccine_name] = ', '.join([d['text'] for d in doses])
        
        return formatted


class ImmunizationResponseDoctor:
    """Format immunization information for doctors"""
    
    @staticmethod
    def format_immunization_records(history, recommendations, patient_id, patient_name=None, age_info=None):
        """
        Format immunization history and recommendations for doctor view
        
        Args:
            history: List of previous immunization records
            recommendations: List of recommended vaccines
            patient_id: Patient external ID
            patient_name: Patient name (optional)
            age_info: Patient age information (dict with 'months' and 'years')
        
        Returns:
            Formatted immunization report string
        """
        report = f"IMMUNIZATION RECORD - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        
        if age_info:
            report += f"\nAge: {age_info.get('years', 'N/A'):.1f} years ({age_info.get('months', 'N/A')} months)"
        
        report += f"\n{'='*80}\n\n"
        
        # Previous immunizations - grouped by vaccine with doses
        report += "IMMUNIZATION HISTORY:\n"
        report += "-" * 80 + "\n"
        if history:
            # Group by vaccine and show doses
            vaccine_doses = ImmunizationResponseFormatter.format_doses_by_vaccine(history)
            for i, (vaccine_name, dose_sequence) in enumerate(vaccine_doses.items(), 1):
                report += f"{i}. {vaccine_name}\n"
                report += f"   {dose_sequence}\n\n"
        else:
            report += "No immunization history found in records.\n\n"
        
        # Recommended vaccines
        report += "-" * 80 + "\n"
        report += "RECOMMENDED UPCOMING VACCINES:\n"
        report += "-" * 80 + "\n"
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec.get('name', 'Unknown vaccine')}\n"
                report += f"   Recommended Age Group(s): {', '.join(rec.get('age_groups', []))}\n"
                report += f"   Total Doses Required: {rec.get('doses', 'Not specified')}\n"
                report += f"   Dosing Interval: {rec.get('interval', 'Not specified')}\n"
                report += f"   Description: {rec.get('description', 'No description')}\n"
                
                if rec.get('contraindications'):
                    report += f"   Contraindications: {', '.join(rec.get('contraindications', []))}\n"
                
                if rec.get('side_effects'):
                    report += f"   Common Side Effects: {', '.join(rec.get('side_effects', []))}\n"
                report += "\n"
        else:
            report += "All age-appropriate vaccines have been administered or patient is not yet at recommended age for additional vaccines.\n\n"
        
        report += "-" * 80 + "\n"
        report += "CLINICAL CONSIDERATIONS:\n"
        report += "• Verify immunization status against official vaccination schedule\n"
        report += "• Check for any contraindications before administering vaccines\n"
        report += "• Document vaccine lot numbers and administration sites\n"
        report += "• Counsel parent/caregiver on expected side effects\n"
        report += "• Review catch-up vaccination if patient is behind schedule\n"
        report += "• Consider immunization requirements for travel\n\n"
        report += "Source: OpenMRS Patient Record + Immunization Schedule Database\n"
        
        return report
    
    @staticmethod
    def format_next_scheduled_dose(next_scheduled, missed_vaccines=None, history=None, patient_id=None, patient_name=None, age_info=None):
        """Format response for doctor asking 'when is next dose' - with clinical detail"""
        report = f"NEXT SCHEDULED IMMUNIZATION - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        if age_info:
            report += f"\nAge: {age_info.get('years', 'N/A'):.1f} years ({age_info.get('months', 'N/A')} months)"
        
        report += f"\n{'='*80}\n\n"
        
        if next_scheduled:
            report += "NEXT SCHEDULED DOSE:\n"
            report += "-" * 80 + "\n"
            report += f"Vaccine: {next_scheduled.get('vaccine_name', 'Unknown')}\n"
            report += f"Scheduled Date: {next_scheduled.get('next_dose_date', 'Not scheduled')}\n"
            report += f"Record Date: {next_scheduled.get('recorded_date', 'Unknown')}\n\n"
        else:
            report += "NO FUTURE DOSES SCHEDULED IN OPENMRS\n"
            report += "Patient appears to be up to date with scheduled vaccinations.\n\n"
        
        if missed_vaccines:
            report += "-" * 80 + "\n"
            report += "VACCINES DUE (Not Yet Administered):\n"
            report += "-" * 80 + "\n"
            for i, vac in enumerate(missed_vaccines, 1):
                report += f"\n{i}. {vac.get('name', 'Unknown vaccine')}\n"
                report += f"   Recommended Age Groups: {', '.join(vac.get('age_groups', []))}\n"
                report += f"   Description: {vac.get('description', 'N/A')}\n"
                if vac.get('contraindications'):
                    report += f"   Contraindications: {', '.join(vac.get('contraindications', []))}\n"
                report += "\n"
        
        if history:
            report += "-" * 80 + "\n"
            report += "RECENT IMMUNIZATION HISTORY:\n"
            report += "-" * 80 + "\n"
            
            # Group by vaccine and show doses
            vaccine_doses = ImmunizationResponseFormatter.format_doses_by_vaccine(history)
            for i, (vaccine_name, dose_sequence) in enumerate(vaccine_doses.items(), 1):
                report += f"{i}. {vaccine_name}\n"
                report += f"   {dose_sequence}\n\n"
        
        report += "-" * 80 + "\n"
        report += "RECOMMENDATIONS:\n"
        report += "• Verify dates with official records\n"
        report += "• Schedule overdue vaccinations immediately\n"
        report += "• Document administration and lot numbers\n\n"
        report += "Source: OpenMRS Patient Record\n"
        
        return report
    
    @staticmethod
    def format_missed_vaccines(missed_vaccines, history=None, patient_id=None, patient_name=None, age_info=None):
        """Format response for doctor asking about 'missed vaccines'"""
        report = f"MISSED/OVERDUE VACCINATIONS - PATIENT {patient_id}"
        if patient_name:
            report += f"\nPatient Name: {patient_name}"
        if age_info:
            report += f"\nAge: {age_info.get('years', 'N/A'):.1f} years ({age_info.get('months', 'N/A')} months)"
        
        report += f"\n{'='*80}\n\n"
        
        if missed_vaccines:
            report += "VACCINES TO BE ADMINISTERED (Age-appropriate, Not Yet Given):\n"
            report += "-" * 80 + "\n"
            for i, vac in enumerate(missed_vaccines, 1):
                report += f"\n{i}. {vac.get('name', 'Unknown vaccine')}\n"
                report += f"   Recommended Age Groups: {', '.join(vac.get('age_groups', []))}\n"
                report += f"   Doses Required: {vac.get('doses', 'Not specified')}\n"
                report += f"   Interval: {vac.get('interval', 'Not specified')}\n"
                report += f"   Description: {vac.get('description', 'N/A')}\n"
                if vac.get('contraindications'):
                    report += f"   Contraindications: {', '.join(vac.get('contraindications', []))}\n"
                if vac.get('side_effects'):
                    report += f"   Expected Side Effects: {', '.join(vac.get('side_effects', []))}\n"
        else:
            report += "Patient is up to date with all age-appropriate vaccines.\n\n"
        
        if history:
            report += "-" * 80 + "\n"
            report += "IMMUNIZATION HISTORY:\n"
            for i, h in enumerate(history, 1):
                report += f"{i}. {h.get('vaccine_name', 'Unknown')} - {h.get('date_given', 'Unknown')}\n"
        
        report += "\n" + "-" * 80 + "\n"
        report += "CLINICAL RECOMMENDATIONS:\n"
        report += "• Prioritize administration of due vaccines\n"
        report += "• Screen for contraindications before administration\n"
        report += "• Document lot numbers, administration sites, and reactions\n"
        report += "• Consider catch-up vaccination if significantly behind\n\n"
        report += "Source: OpenMRS Patient Record + Vaccination Schedule\n"
        
        return report

    @staticmethod
    def format_last_administered_vaccine(history, patient_id=None, patient_name=None):
        """
        Format the LAST/MOST RECENT administered vaccine for doctor view
        Shows only the most recently given vaccination
        """
        report = ""
        
        if patient_name:
            report += f"MOST RECENT VACCINATION - PATIENT {patient_id} ({patient_name})\n"
        else:
            report += f"MOST RECENT VACCINATION - PATIENT {patient_id}\n"
        
        report += "=" * 80 + "\n"
        
        if history and len(history) > 0:
            # Get the most recent vaccination (first in list if sorted by date)
            last_vac = history[0]
            report += f"Vaccine: {last_vac.get('vaccine_name', 'Unknown')}\n"
            report += f"Date Given: {last_vac.get('date_given', 'Unknown')}\n"
            if last_vac.get('dose_number'):
                report += f"Dose Number: {last_vac.get('dose_number')}\n"
            if last_vac.get('administration_site'):
                report += f"Administration Site: {last_vac.get('administration_site')}\n"
            if last_vac.get('manufacturer'):
                report += f"Manufacturer: {last_vac.get('manufacturer')}\n"
            if last_vac.get('lot_number'):
                report += f"Lot Number: {last_vac.get('lot_number')}\n"
            if last_vac.get('adverse_events'):
                report += f"Adverse Events Reported: {last_vac.get('adverse_events')}\n"
        else:
            report += "No vaccination history found for this patient.\n"
        
        report += "=" * 80 + "\n"
        report += "Source: OpenMRS Patient Record\n"
        
        return report


class ImmunizationResponsePatient:
    """Format immunization information for patients"""
    
    @staticmethod
    def format_immunization_records(history, recommendations, patient_name=None, age_info=None):
        """
        Format immunization history and recommendations for patient view
        
        Args:
            history: List of previous immunization records
            recommendations: List of recommended vaccines
            patient_name: Patient name (optional)
            age_info: Patient age information (dict with 'months' and 'years')
        
        Returns:
            Formatted immunization report string
        """
        report = "**Your Child's Immunization Record**\n"
        if patient_name:
            report += f"Patient: {patient_name}\n"
        
        if age_info:
            report += f"Age: {age_info.get('years', 'N/A'):.1f} years ({age_info.get('months', 'N/A')} months)\n"
        
        report += f"\n{'='*70}\n\n"
        
        # Previous immunizations - in patient-friendly language
        report += "**Vaccines Your Child Has Received:**\n"
        report += "-" * 70 + "\n"
        if history:
            # Group by vaccine and show doses
            vaccine_doses = ImmunizationResponseFormatter.format_doses_by_vaccine(history)
            for i, (vaccine_name, dose_sequence) in enumerate(vaccine_doses.items(), 1):
                report += f"{i}. **{vaccine_name}**\n"
                report += f"   {dose_sequence}\n\n"
        else:
            report += "No vaccine records found. Please consult with your healthcare provider.\n\n"
        
        # Recommended vaccines - in simple language
        report += "-" * 70 + "\n"
        report += "**Upcoming Vaccines for This Age:**\n"
        report += "-" * 70 + "\n"
        if recommendations:
            report += f"Your child is due for {len(recommendations)} vaccine(s):\n\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"**{i}. {rec.get('name', 'Unknown vaccine')}**\n"
                report += f"   What it protects against: {rec.get('description', 'Not specified')}\n"
                report += f"   Number of doses needed: {rec.get('doses', 'Not specified')}\n"
                report += f"   Interval between doses: {rec.get('interval', 'Not specified')}\n"
                
                if rec.get('side_effects'):
                    side_effects_text = ', '.join(rec.get('side_effects', [])[:3])
                    report += f"   Common reactions: {side_effects_text}\n"
                
                report += "\n"
        else:
            report += "Your child is up-to-date with all age-appropriate vaccines!\n\n"
        
        report += "-" * 70 + "\n"
        report += "**Important Information:**\n"
        report += "• Bring this record to all health visits\n"
        report += "• Vaccines protect your child from serious diseases\n"
        report += "• Some mild reactions are normal (fever, soreness at injection site)\n"
        report += "• Serious reactions are very rare\n"
        report += "• Talk to your doctor about vaccine schedule\n"
        report += "• Keep all vaccination records for school and travel\n\n"
        report += "Source: Your Medical Record\n"
        
        return report
    
    @staticmethod
    def format_next_scheduled_dose(next_scheduled, missed_vaccines=None, patient_name=None, age_info=None):
        """Format response for 'when is next dose' questions"""
        report = f"**Your Child's Next Vaccination**\n\n"
        
        if patient_name:
            report += f"Patient: {patient_name}\n"
        if age_info:
            report += f"Age: {age_info.get('years', 'N/A'):.1f} years\n"
        
        report += "=" * 70 + "\n\n"
        
        if next_scheduled:
            report += "**NEXT SCHEDULED DOSE:**\n"
            report += "-" * 70 + "\n"
            report += f"Vaccine: {next_scheduled.get('vaccine_name', 'Unknown')}\n"
            report += f"Scheduled Date: {next_scheduled.get('next_dose_date', 'Not scheduled')}\n\n"
        else:
            report += "**NO FUTURE DOSES SCHEDULED**\n"
            report += "Your child appears to be up to date with scheduled vaccinations.\n\n"
        
        if missed_vaccines:
            report += "-" * 70 + "\n"
            report += f"**VACCINES DUE (MISSED):**\n"
            for i, vac in enumerate(missed_vaccines, 1):
                report += f"\n{i}. {vac.get('name', 'Unknown vaccine')}\n"
                report += f"   Description: {vac.get('description', 'N/A')}\n"
            report += "\n"
        
        report += "-" * 70 + "\n"
        report += "Please contact your healthcare provider to schedule these vaccines.\n"
        
        return report
    
    @staticmethod
    def format_missed_vaccines(missed_vaccines, patient_name=None, age_info=None):
        """Format response for 'missed vaccines' questions"""
        report = f"**Vaccines Your Child Needs**\n\n"
        
        if patient_name:
            report += f"Patient: {patient_name}\n"
        if age_info:
            report += f"Age: {age_info.get('years', 'N/A'):.1f} years\n"
        
        report += "=" * 70 + "\n\n"
        
        if missed_vaccines:
            report += f"**VACCINES TO BE GIVEN (Age-appropriate):**\n"
            report += "-" * 70 + "\n"
            for i, vac in enumerate(missed_vaccines, 1):
                report += f"\n{i}. {vac.get('name', 'Unknown vaccine')}\n"
                report += f"   Recommended Age: {', '.join(vac.get('age_groups', []))}\n"
                report += f"   Description: {vac.get('description', 'N/A')}\n"
                if vac.get('side_effects'):
                    report += f"   Common Side Effects: {', '.join(vac.get('side_effects', []))}\n"
                report += "\n"
        else:
            report += "Your child is up to date with all age-appropriate vaccines!\n\n"
        
        report += "-" * 70 + "\n"
        report += "Talk with your pediatrician to schedule these vaccinations.\n"
        
        return report

    @staticmethod
    def format_last_administered_vaccine(history, patient_name=None, age_info=None):
        """
        Format the LAST/MOST RECENT administered vaccine for patient view
        Shows only the most recently given vaccination
        """
        report = "**Your Child's Most Recent Vaccination**\n\n"
        
        if patient_name:
            report += f"Patient: {patient_name}\n"
        if age_info:
            report += f"Age: {age_info.get('years', 'N/A'):.1f} years\n"
        
        report += "=" * 70 + "\n\n"
        
        if history and len(history) > 0:
            # Get the most recent vaccination (first in list if sorted by date)
            last_vac = history[0]
            report += f"**Vaccine:** {last_vac.get('vaccine_name', 'Unknown')}\n"
            report += f"**Date Given:** {last_vac.get('date_given', 'Unknown')}\n"
            if last_vac.get('dose_number'):
                report += f"**Dose Number:** {last_vac.get('dose_number')}\n"
            if last_vac.get('administration_site'):
                report += f"**Where:** {last_vac.get('administration_site')}\n"
            if last_vac.get('adverse_events'):
                report += f"**Reactions:** {last_vac.get('adverse_events')}\n"
            else:
                report += "**Reactions:** No adverse events reported\n"
        else:
            report += "No vaccination history found for your child.\n"
        
        report += "\n" + "=" * 70 + "\n"
        report += "Contact your healthcare provider for more information.\n"
        
        return report
