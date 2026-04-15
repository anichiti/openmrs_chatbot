"""
Immunization OpenMRS Fetcher
Retrieves immunization history from OpenMRS database for a patient
and determines recommended vaccinations based on age
"""

import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database.db import OpenMRSDatabase
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ImmunizationOpenMRSFetcher:
    """Fetch immunization history and recommendations from OpenMRS"""
    
    def __init__(self):
        self.db = None
        self.vaccines = self._load_vaccine_data()
    
    def _load_vaccine_data(self):
        """Load vaccine data from immunization.json"""
        try:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            immunization_file = os.path.join(data_dir, 'immunization.json')
            
            if os.path.exists(immunization_file):
                with open(immunization_file, 'r') as f:
                    data = json.load(f)
                    return data.get('vaccines', [])
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error loading vaccine data: {e}")
        
        return []
    
    def _resolve_patient_id(self, patient_external_id):
        """Resolve external patient ID to internal ID"""
        try:
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            query = '''
            SELECT p.PATIENT_ID 
            FROM patient p
            JOIN patient_identifier pi ON p.PATIENT_ID = pi.PATIENT_ID
            WHERE pi.IDENTIFIER = %s 
            LIMIT 1
            '''
            cursor.execute(query, (patient_external_id,))
            result = cursor.fetchone()
            
            if result:
                internal_id = result[0]
                logger.info(f"[IMMUNIZATION] Found patient {patient_external_id} (internal ID: {internal_id})")
                return internal_id
            else:
                logger.error(f"[IMMUNIZATION] Patient {patient_external_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error resolving patient ID: {e}")
            return None
    
    def _get_patient_birthdate(self, internal_id):
        """Get patient's birthdate"""
        try:
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            query = 'SELECT BIRTHDATE FROM person WHERE PERSON_ID = %s'
            cursor.execute(query, (internal_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                birthdate = result[0]
                logger.info(f"[IMMUNIZATION] Patient birthdate: {birthdate}")
                return birthdate
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error getting birthdate: {e}")
        
        return None
    
    def _calculate_age_months(self, birthdate):
        """Calculate patient age in months"""
        try:
            today = datetime.now().date()
            if isinstance(birthdate, str):
                birthdate = datetime.strptime(birthdate, '%Y-%m-%d').date()
            
            age_delta = relativedelta(today, birthdate)
            total_months = age_delta.years * 12 + age_delta.months
            return total_months
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error calculating age: {e}")
            return 0
    
    def get_immunization_history(self, patient_id):
        """
        Get patient's immunization history from OpenMRS with ACTUAL vaccination dates
        
        Returns:
            List of vaccination records with actual dates given
        """
        try:
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return []
            
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            
            # Query to get actual vaccination dates from the obs_group structure
            query = '''
            SELECT DISTINCT
                parent_o.obs_id,
                vac_o.value_coded,
                vaccine_cn.name as vaccine_name,
                COALESCE(vac_date_o.value_datetime, vac_date_text_o.value_text, parent_o.obs_datetime) as actual_vac_date,
                next_dose_o.value_datetime as next_dose_date,
                seq_o.value_numeric as dose_number
            FROM obs parent_o
            JOIN obs vac_o ON vac_o.obs_group_id = parent_o.obs_id
            JOIN concept vac_c ON vac_o.concept_id = vac_c.CONCEPT_ID
            JOIN concept_name vac_concept_cn ON vac_c.CONCEPT_ID = vac_concept_cn.CONCEPT_ID
            JOIN concept vaccine_concept ON vac_o.value_coded = vaccine_concept.CONCEPT_ID
            JOIN concept_name vaccine_cn ON vaccine_concept.CONCEPT_ID = vaccine_cn.CONCEPT_ID
            LEFT JOIN obs vac_date_o ON vac_date_o.obs_group_id = parent_o.obs_id 
                AND vac_date_o.concept_id IN (
                    SELECT c.CONCEPT_ID FROM concept c
                    JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
                    WHERE cn.name IN ('Immunization date', 'Vaccination date')
                    AND vac_date_o.voided = 0
                )
            LEFT JOIN obs vac_date_text_o ON vac_date_text_o.obs_group_id = parent_o.obs_id
                AND vac_date_text_o.concept_id IS NOT NULL
                AND vac_date_text_o.value_text IS NOT NULL
                AND vac_date_text_o.voided = 0
            LEFT JOIN obs next_dose_o ON next_dose_o.obs_group_id = parent_o.obs_id
                AND next_dose_o.concept_id IN (
                    SELECT c.CONCEPT_ID FROM concept c
                    JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
                    WHERE cn.name = 'Date of next dose'
                    AND next_dose_o.voided = 0
                )
            LEFT JOIN obs seq_o ON seq_o.obs_group_id = parent_o.obs_id
                AND seq_o.concept_id IN (
                    SELECT c.CONCEPT_ID FROM concept c
                    JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
                    WHERE cn.name IN ('Immunization sequence number', 'Vaccination sequence number')
                    AND seq_o.voided = 0
                )
            WHERE parent_o.person_id = %s
            AND vac_concept_cn.name IN ('Immunizations', 'Immunisation', 'Vaccination', 'IMMUNIZATIONS')
            AND parent_o.voided = 0
            AND vac_o.voided = 0
            AND vaccine_cn.concept_name_type = 'FULLY_SPECIFIED'
            ORDER BY actual_vac_date DESC, vaccine_cn.name
            '''
            
            cursor.execute(query, (internal_id,))
            results = cursor.fetchall()
            
            vaccinations = []
            seen_obs_ids = set()
            
            for row in results:
                obs_id = row[0]
                # Skip duplicate records (same obs_id with different language concept names)
                if obs_id in seen_obs_ids:
                    continue
                seen_obs_ids.add(obs_id)
                
                vac = {
                    'obs_id': obs_id,
                    'date_given': str(row[3]) if row[3] else 'Unknown',
                    'vaccine_name': row[2] if row[2] else 'Unknown Vaccine',
                    'vaccine_concept_id': row[1],
                    'next_dose_date': str(row[4]) if row[4] else None,
                    'dose_number': int(row[5]) if row[5] else None
                }
                vaccinations.append(vac)
            
            logger.info(f"[IMMUNIZATION] Found {len(vaccinations)} immunization records for patient {patient_id}")
            return vaccinations
            
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error fetching immunization history: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _check_age_match(self, age_months, age_groups):
        """
        Check if patient age matches any of the recommended age groups
        
        Args:
            age_months: Patient age in months
            age_groups: List of age group strings like ["2 months", "4-6 years", etc]
        
        Returns:
            bool: True if age matches any group
        """
        if not isinstance(age_groups, list):
            return False
        
        for age_group in age_groups:
            if not isinstance(age_group, str):
                continue
            
            age_group = age_group.strip().lower()
            
            # Handle specific month references (e.g., "2 months", "6 months")
            if 'months' in age_group:
                try:
                    if '-' in age_group:
                        # Range like "12-15 months"
                        parts = age_group.replace('months', '').split('-')
                        min_months = int(parts[0].strip())
                        max_months = int(parts[1].strip())
                        if min_months <= age_months <= max_months:
                            return True
                    else:
                        # Single value or "x months and older"
                        if 'and older' in age_group:
                            # "6 months and older"
                            months = int(age_group.replace('months', '').replace('and older', '').strip())
                            if age_months >= months:
                                return True
                        else:
                            # "6 months"
                            months = int(age_group.replace('months', '').strip())
                            if age_months >= months:
                                return True
                except (ValueError, IndexError):
                    continue
            
            # Handle year-based ranges (e.g., "4-6 years")
            elif 'years' in age_group:
                try:
                    if '-' in age_group:
                        # Range like "4-6 years"
                        parts = age_group.replace('years', '').split('-')
                        min_years = int(parts[0].strip())
                        max_years = int(parts[1].strip())
                        age_years = age_months / 12.0
                        if min_years <= age_years < (max_years + 1):
                            return True
                    else:
                        # Single value like "Adult td every 10 years" (skip)
                        if 'adult' in age_group or 'every' in age_group:
                            continue
                except (ValueError, IndexError):
                    continue
        
        return False

    def get_recommended_vaccines(self, patient_id):
        """
        Get recommended vaccines based on patient age
        
        Returns:
            List of recommended vaccines with schedules
        """
        try:
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return []
            
            birthdate = self._get_patient_birthdate(internal_id)
            if not birthdate:
                return []
            
            age_months = self._calculate_age_months(birthdate)
            age_years = age_months / 12
            
            logger.info(f"[IMMUNIZATION] Patient age: {age_months} months ({age_years:.1f} years)")
            
            # Get immunization history to exclude already given vaccines
            history = self.get_immunization_history(patient_id)
            # Create set of vaccine names that have been given (normalized)
            given_vaccine_names = set()
            for vac in history:
                name = vac.get('vaccine_name', '').lower().strip()
                given_vaccine_names.add(name)
            
            logger.info(f"[IMMUNIZATION] Previously given vaccines: {given_vaccine_names}")
            
            # Match vaccines to age
            recommended = []
            
            for vaccine in self.vaccines:
                vaccine_name = vaccine.get('name', '')
                vaccine_name_lower = vaccine_name.lower().strip()
                
                # Check if this exact vaccine was already given
                already_given = False
                for given in given_vaccine_names:
                    # Only skip if it's an exact match
                    if given == vaccine_name_lower:
                        already_given = True
                        logger.info(f"[IMMUNIZATION] Skipping {vaccine_name} (already given)")
                        break
                
                if already_given:
                    continue
                
                # Check age groups using robust matching
                age_groups = vaccine.get('recommended_age_groups', [])
                if self._check_age_match(age_months, age_groups):
                    recommended.append({
                        'name': vaccine.get('name'),
                        'age_groups': vaccine.get('recommended_age_groups'),
                        'doses': vaccine.get('number_of_doses'),
                        'interval': vaccine.get('interval_between_doses'),
                        'description': vaccine.get('description'),
                        'side_effects': vaccine.get('side_effects', []),
                        'contraindications': vaccine.get('contraindications', []),
                        'type': vaccine.get('type', ''),
                        'efficacy': vaccine.get('efficacy', {})
                    })
                    logger.info(f"[IMMUNIZATION] Recommending {vaccine_name} for age {age_months} months")
            
            logger.info(f"[IMMUNIZATION] Found {len(recommended)} recommended vaccines for age {age_months} months")
            return recommended
            
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error getting recommended vaccines: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_next_scheduled_dose(self, patient_id):
        """
        Get the NEXT SCHEDULED dose from OpenMRS database
        
        Returns:
            Dict with next scheduled vaccine, date, and vaccine type or None if none scheduled
        """
        try:
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return None
            
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            
            # Get the next scheduled dose from obs_group
            query = '''
            SELECT DISTINCT
                vaccine_cn.name as vaccine_name,
                MIN(next_dose_o.value_datetime) as next_dose_date,
                parent_o.obs_datetime as recorded_date
            FROM obs parent_o
            JOIN obs vac_o ON vac_o.obs_group_id = parent_o.obs_id
            JOIN concept vac_c ON vac_o.concept_id = vac_c.CONCEPT_ID
            JOIN concept_name vac_concept_cn ON vac_c.CONCEPT_ID = vac_concept_cn.CONCEPT_ID
            JOIN concept vaccine_concept ON vac_o.value_coded = vaccine_concept.CONCEPT_ID
            JOIN concept_name vaccine_cn ON vaccine_concept.CONCEPT_ID = vaccine_cn.CONCEPT_ID
            JOIN obs next_dose_o ON next_dose_o.obs_group_id = parent_o.obs_id
                AND next_dose_o.concept_id IN (
                    SELECT c.CONCEPT_ID FROM concept c
                    JOIN concept_name cn ON c.CONCEPT_ID = cn.CONCEPT_ID
                    WHERE cn.name = 'Date of next dose'
                )
            WHERE parent_o.person_id = %s
            AND vac_concept_cn.name IN ('Immunizations', 'Immunisation', 'Vaccination', 'IMMUNIZATIONS')
            AND next_dose_o.value_datetime IS NOT NULL
            AND next_dose_o.value_datetime > NOW()
            AND parent_o.voided = 0
            AND vac_o.voided = 0
            AND next_dose_o.voided = 0
            AND vaccine_cn.concept_name_type = 'FULLY_SPECIFIED'
            GROUP BY vaccine_cn.name, parent_o.obs_datetime
            ORDER BY next_dose_date ASC
            LIMIT 1
            '''
            
            cursor.execute(query, (internal_id,))
            result = cursor.fetchone()
            
            if result:
                next_dose = {
                    'vaccine_name': result[0],
                    'next_dose_date': str(result[1]) if result[1] else None,
                    'recorded_date': str(result[2]) if result[2] else None
                }
                logger.info(f"[IMMUNIZATION] Next scheduled dose: {next_dose['vaccine_name']} on {next_dose['next_dose_date']}")
                return next_dose
            else:
                logger.info(f"[IMMUNIZATION] No future scheduled doses found")
                return None
                
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error fetching next scheduled dose: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_missed_vaccines(self, patient_id):
        """
        Get vaccines that SHOULD have been given based on age but HAVEN'T been given yet
        (Overdue vaccines based on age and vaccination schedule)
        
        Returns:
            List of missed/overdue vaccines
        """
        try:
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return []
            
            birthdate = self._get_patient_birthdate(internal_id)
            if not birthdate:
                return []
            
            age_months = self._calculate_age_months(birthdate)
            
            # Get what's been given
            history = self.get_immunization_history(patient_id)
            given_vaccine_names = set()
            for vac in history:
                name = vac.get('vaccine_name', '').lower().strip()
                given_vaccine_names.add(name)
            
            logger.info(f"[IMMUNIZATION] Age: {age_months} months, Given vaccines: {given_vaccine_names}")
            
            # Find vaccines that are overdue (not yet given but age-appropriate)
            missed = []
            for vaccine in self.vaccines:
                vaccine_name = vaccine.get('name', '')
                vaccine_name_lower = vaccine_name.lower().strip()
                
                # Skip if already given
                if vaccine_name_lower in given_vaccine_names:
                    continue
                
                # Check if vaccine is age-appropriate  (should have been given)
                age_groups = vaccine.get('recommended_age_groups', [])
                if self._check_age_match(age_months, age_groups):
                    missed.append({
                        'name': vaccine.get('name'),
                        'age_groups': vaccine.get('recommended_age_groups'),
                        'doses': vaccine.get('number_of_doses'),
                        'interval': vaccine.get('interval_between_doses'),
                        'description': vaccine.get('description'),
                        'contraindications': vaccine.get('contraindications', []),
                        'side_effects': vaccine.get('side_effects', []),
                        'type': vaccine.get('type', ''),
                        'efficacy': vaccine.get('efficacy', {}),
                        'is_overdue': True  # Mark as overdue since age has already passed
                    })
                    logger.info(f"[IMMUNIZATION] Missed vaccine: {vaccine_name} (overdue for age {age_months} months)")
            
            logger.info(f"[IMMUNIZATION] Found {len(missed)} missed/overdue vaccines")
            return missed
            
        except Exception as e:
            logger.error(f"[IMMUNIZATION] Error getting missed vaccines: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def disconnect(self):
        """Close database connection"""
        if self.db:
            self.db.disconnect()
