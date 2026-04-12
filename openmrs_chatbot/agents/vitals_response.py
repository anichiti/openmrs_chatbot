"""
Vitals Response Formatters
Formats vital signs data for patient vs doctor presentation
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta

class VitalsResponseDoctor:
    """Format vital signs for doctor/clinical view"""
    
    @staticmethod
    def format_vitals(vitals, patient_data, patient_id, patient_name):
        """
        Format vitals for doctor with clinical detail
        
        Args:
            vitals: List of vital observations
            patient_data: Full patient data dict with demographics
            patient_id: Patient ID
            patient_name: Patient full name
        
        Returns:
            Formatted clinical vitals report
        """
        response = f"**CLINICAL VITAL SIGNS REPORT**\n"
        response += f"Patient: {patient_name or patient_id}\n"
        response += f"Record ID: {patient_id}\n"
        response += "-" * 70 + "\n\n"
        
        if not vitals:
            response += "No vital signs data available in system.\n"
            return response
        
        # Extract vitals with detailed mapping
        # IMPORTANT: Keys must match actual OpenMRS database vital_name field values (case-insensitive)
        vital_mapping = {
            'weight': ('Weight', 'kg'),
            'height': ('Height', 'cm'),
            'length': ('Length', 'cm'),
            'temperature': ('Temperature', '°C'),
            'systolic blood pressure': ('BP Systolic', 'mmHg'),
            'diastolic blood pressure': ('BP Diastolic', 'mmHg'),
            'heart rate': ('Heart Rate', 'bpm'),
            'pulse': ('Pulse', 'bpm'),
            'oxygen saturation': ('SpO2', '%'),
            'respiratory rate': ('RR', 'breaths/min'),
            'head circumference': ('HC', 'cm'),
            'body mass index': ('BMI', 'kg/m²'),
        }
        
        vitals_found = {}
        most_recent_date = None
        
        for vital in vitals:
            vital_name = vital.get('vital_name', '').lower()
            vital_value = vital.get('value_numeric')
            vital_date = vital.get('obs_datetime', '')
            
            # Update most recent date
            if vital_date and (not most_recent_date or vital_date > most_recent_date):
                most_recent_date = vital_date
            
            # Match vital to mapping
            for search_key, (display_name, unit) in vital_mapping.items():
                if search_key in vital_name:
                    vitals_found[display_name] = (vital_value, unit, vital_date)
                    break
        
        # Calculate BMI if not directly available
        if 'BMI' not in vitals_found and 'Weight' in vitals_found and 'Height' in vitals_found:
            w_val = vitals_found['Weight'][0]
            h_val = vitals_found['Height'][0]
            if w_val and h_val and h_val > 0:
                bmi = round(float(w_val) / ((float(h_val) / 100) ** 2), 1)
                vitals_found['BMI'] = (bmi, 'kg/m²', '')
        
        # Display vitals in clinical order
        response += "**MEASUREMENTS:**\n"
        clinical_order = ['BP Systolic', 'BP Diastolic', 'Heart Rate', 'Pulse', 'RR', 'Temperature', 
                         'SpO2', 'Weight', 'Height', 'Length', 'HC', 'BMI']
        
        for key in clinical_order:
            if key in vitals_found:
                value, unit, date = vitals_found[key]
                if value:
                    response += f"• {key}: {value} {unit}\n"
        
        if most_recent_date:
            response += f"\nRecorded: {most_recent_date}\n\n"
        
        # Clinical assessment section for doctor
        response += "**CLINICAL NOTES:**\n"
        response += "-" * 70 + "\n"
        
        # Extract patient info for age calculation
        patient_info_data = patient_data.get("patient", {}).get("data", [])
        if patient_info_data:
            birthdate = patient_info_data[0].get("birthdate")
            if birthdate:
                try:
                    birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d').date() if isinstance(birthdate, str) else birthdate
                    age_delta = relativedelta(datetime.now().date(), birthdate_obj)
                    age_years = age_delta.years + age_delta.months / 12
                    age_months = age_delta.years * 12 + age_delta.months
                    
                    response += f"Age: {age_years:.1f} years ({age_months} months)\n"
                    
                    # Normal ranges for age group (pediatric)
                    if age_years < 2:
                        response += "Age Group: Infant (<2 years) - normal ranges vary significantly\n"
                    elif age_years < 6:
                        response += "Age Group: Preschool (2-6 years)\n"
                    elif age_years < 13:
                        response += "Age Group: School age (6-13 years)\n"
                    else:
                        response += "Age Group: Adolescent (13+ years)\n"
                except Exception as e:
                    pass
        
        response += "\nFor age-appropriate reference ranges, consult:\n"
        response += "- WHO growth charts (0-18 years)\n"
        response += "- Pediatric vital sign standards\n"
        response += "- Patient BMI percentile charts (pediatric)\n"
        
        return response
    
    @staticmethod
    def format_growth_assessment(vitals, patient_data, patient_id, patient_name):
        """Format growth assessment for doctor"""
        response = f"**GROWTH ASSESSMENT - {patient_name or patient_id}**\n\n"
        
        # Extract weight and height
        weight_kg = None
        height_cm = None
        
        for vital in vitals:
            vital_name = vital.get('vital_name', '').lower()
            if 'weight' in vital_name:
                weight_kg = vital.get('value_numeric')
            elif 'height' in vital_name or 'length' in vital_name:
                height_cm = vital.get('value_numeric')
        
        # Calculate BMI
        if weight_kg and height_cm:
            height_m = height_cm / 100
            bmi = weight_kg / (height_m ** 2)
            response += f"BMI: {bmi:.1f} kg/m²\n"
            response += f"Weight: {weight_kg} kg, Height: {height_cm} cm\n\n"
            
            # Doctor notes on BMI
            response += "**BMI Assessment:**\n"
            response += "- Use WHO growth charts for pediatric patients (<18 years)\n"
            response += "- Adult BMI categories may not apply to children\n"
            response += "- Consider height velocity and growth pattern trends\n"
        else:
            response += "Insufficient data for growth assessment (weight and/or height missing)\n"
        
        return response


class VitalsResponsePatient:
    """Format vital signs for patient/parent-friendly view"""
    
    @staticmethod
    def format_vitals(vitals, patient_name, age_info):
        """
        Format vitals for patient/parent with simple language
        
        Args:
            vitals: List of vital observations
            patient_name: Patient first name
            age_info: Dict with 'years' and 'months' keys
        
        Returns:
            Formatted patient-friendly vitals report
        """
        response = f"**Your Child's Health Measurements**\n\n"
        
        if not vitals:
            response += "No recent health measurements on file.\n"
            return response
        
        # Simple vital mapping for patients
        # IMPORTANT: Keys must match actual OpenMRS database vital_name field values (case-insensitive)
        vital_mapping = {
            'weight': ('Weight', 'kg'),
            'height': ('Height', 'cm'),
            'length': ('Length', 'cm'),
            'temperature': ('Temperature', '°C'),
            'systolic blood pressure': ('Blood Pressure (upper number)', 'mmHg'),
            'diastolic blood pressure': ('Blood Pressure (lower number)', 'mmHg'),
            'heart rate': ('Heart Rate', 'beats per minute'),
            'pulse': ('Pulse', 'beats per minute'),
            'oxygen saturation': ('Oxygen Level', '%'),
            'respiratory rate': ('Breathing Rate', 'breaths per minute'),
            'head circumference': ('Head Size', 'cm'),
        }
        
        vitals_found = {}
        for vital in vitals:
            vital_name = vital.get('vital_name', '').lower()
            vital_value = vital.get('value_numeric')
            
            for search_key, (display_name, unit) in vital_mapping.items():
                if search_key in vital_name:
                    vitals_found[display_name] = (vital_value, unit)
                    break
        
        # Display in simple format
        if vitals_found:
            for display_name, (value, unit) in vitals_found.items():
                if value:
                    response += f"• **{display_name}:** {value} {unit}\n"
        
        # Add reassuring note
        response += f"\n**Note:** These measurements were taken at your child's last doctor visit.\n"
        
        if age_info:
            response += f"Your child is {age_info.get('months', 0)} months old.\n"
        
        response += "\n**Important:** Each child grows at their own pace. Your doctor monitors "
        response += f"whether these measurements are healthy for {patient_name}'s age and growth pattern."
        
        return response
    
    @staticmethod
    def format_growth_summary(vitals, patient_name, age_info):
        """Format simple growth summary for parent"""
        response = f"**Growth Information**\n\n"
        response += f"{patient_name} is growing well! Here's what we know:\n\n"
        
        # Extract weight and height
        weight_kg = None
        height_cm = None
        
        for vital in vitals:
            vital_name = vital.get('vital_name', '').lower()
            if 'weight' in vital_name:
                weight_kg = vital.get('value_numeric')
            elif 'height' in vital_name or 'length' in vital_name:
                height_cm = vital.get('value_numeric')
        
        if weight_kg:
            response += f"• **Weight:** {weight_kg} kg\n"
        if height_cm:
            response += f"• **Height/Length:** {height_cm} cm\n"
        
        # Calculate BMI if available
        if weight_kg and height_cm:
            height_m = height_cm / 100
            bmi = weight_kg / (height_m ** 2)
            response += f"• **Growth Index:** {bmi:.1f}\n"
        
        response += f"\nYour doctor compares these to standard growth charts for {patient_name}'s age to ensure healthy development.\n"
        response += "If you have concerns about your child's growth, talk to your doctor at the next visit."
        
        return response
