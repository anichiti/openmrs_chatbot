"""
Allergy OpenMRS Fetcher
Retrieves patient allergies from OpenMRS database
"""

from database.db import OpenMRSDatabase
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AllergyOpenMRSFetcher:
    """Fetch patient allergies from OpenMRS database"""
    
    def __init__(self):
        self.db = None
    
    def _resolve_patient_id(self, patient_external_id):
        """
        Resolve patient external ID (e.g., 100008E) to internal ID
        
        Args:
            patient_external_id: External patient ID (e.g., 100008E)
        
        Returns:
            Internal patient ID (integer) or None if not found
        """
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
                logger.info(f"[ALLERGY] Found patient {patient_external_id} (internal ID: {internal_id})")
                return internal_id
            else:
                logger.warning(f"[ALLERGY] Patient {patient_external_id} not found in system")
                return None
                
        except Exception as e:
            logger.error(f"[ALLERGY] Error resolving patient ID: {e}")
            return None
    
    def get_patient_allergies(self, patient_id):
        """
        Get all patient allergies
        
        Args:
            patient_id: Patient ID (external, e.g., 100008E)
        
        Returns:
            Dict with allergen_type -> [allergens] mapping
        """
        try:
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            # Resolve external ID to internal ID
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return {}
            
            cursor = self.db.connection.cursor()
            
            # Query distinct allergies with English/preferred severity name
            # This gets the PREFERRED name with locale 'en' (English) for severity
            # Falls back to FULLY_SPECIFIED if no PREFERRED English name exists
            query = '''
            SELECT DISTINCT
                a.ALLERGY_ID,
                cn_allergen.NAME as ALLERGEN_NAME,
                a.ALLERGEN_TYPE,
                COALESCE(
                    (SELECT cn.NAME FROM concept_name cn 
                     WHERE cn.CONCEPT_ID = a.SEVERITY_CONCEPT_ID 
                     AND cn.CONCEPT_NAME_TYPE = 'PREFERRED' 
                     AND cn.LOCALE = 'en'
                     LIMIT 1),
                    (SELECT cn.NAME FROM concept_name cn 
                     WHERE cn.CONCEPT_ID = a.SEVERITY_CONCEPT_ID 
                     AND cn.CONCEPT_NAME_TYPE = 'FULLY_SPECIFIED'
                     AND cn.LOCALE = 'en'
                     LIMIT 1),
                    (SELECT cn.NAME FROM concept_name cn 
                     WHERE cn.CONCEPT_ID = a.SEVERITY_CONCEPT_ID 
                     LIMIT 1)
                ) as SEVERITY,
                a.COMMENTS,
                a.DATE_CREATED
            FROM allergy a
            LEFT JOIN concept_name cn_allergen ON a.CODED_ALLERGEN = cn_allergen.CONCEPT_ID 
                AND cn_allergen.CONCEPT_NAME_TYPE = 'FULLY_SPECIFIED'
            WHERE a.PATIENT_ID = %s
            AND a.VOIDED = 0
            ORDER BY a.ALLERGEN_TYPE, cn_allergen.NAME
            '''
            
            cursor.execute(query, (internal_id,))
            results = cursor.fetchall()
            
            # Group by allergen type with smart deduplication
            allergies_by_type = {}
            
            # Map of allergen name variations to canonical names (handle different languages)
            allergen_name_map = {
                'dust': ['dust', 'poussière', 'pousyè', 'poussiere'],  # Dust in multiple languages/spellings
            }
            
            def normalize_allergen_name(name):
                """Normalize allergen name to canonical form for deduplication"""
                if not name:
                    return None
                name_lower = name.lower().strip()
                for canonical, variations in allergen_name_map.items():
                    if name_lower in variations:
                        return canonical
                return name_lower
            
            for row in results:
                allergen_name = row[1]
                allergen_type = row[2]
                severity = row[3]  # Use OpenMRS severity value directly
                
                if not allergen_name:
                    continue
                
                if allergen_type not in allergies_by_type:
                    allergies_by_type[allergen_type] = []
                
                allergen_info = {
                    'name': allergen_name,
                    'severity': severity,
                    'comments': row[4],
                    'date_recorded': str(row[5]) if row[5] else None
                }
                
                # Avoid duplicates - normalize names for comparison
                normalized_current = normalize_allergen_name(allergen_name)
                is_duplicate = any(
                    normalize_allergen_name(a['name']) == normalized_current 
                    for a in allergies_by_type[allergen_type]
                )
                
                if not is_duplicate:
                    allergies_by_type[allergen_type].append(allergen_info)
            
            logger.info(f"[ALLERGY] Found {len(results)} allergy records for patient {patient_id}")
            return allergies_by_type
            
        except Exception as e:
            logger.error(f"[ALLERGY] Error fetching allergies: {e}")
            return {}
    
    def check_drug_allergy(self, patient_id, drug_name):
        """
        Check if a drug is contraindicated due to allergies
        
        Args:
            patient_id: Patient ID (external, e.g., 100008E)
            drug_name: Drug name to check (e.g., "penicillin", "amoxicillin")
        
        Returns:
            Dict with:
            - is_contraindicated: bool
            - allergen_matched: str (name of allergen if matched)
            - severity: str  
            - message: str (explanation)
        """
        try:
            allergies = self.get_patient_allergies(patient_id)
            
            if not allergies or 'DRUG' not in allergies:
                return {
                    'is_contraindicated': False,
                    'allergen_matched': None,
                    'severity': None,
                    'message': f'No drug allergies found for patient {patient_id}'
                }
            
            drug_lower = drug_name.lower()
            drug_allergies = allergies.get('DRUG', [])
            
            # Check for matching allergens
            for allergen in drug_allergies:
                allergen_name = allergen['name'].lower() if allergen['name'] else ''
                
                # Check for exact match or class match (e.g., "penicillin" matches "Penicillin drug class")
                if drug_lower in allergen_name or allergen_name in drug_lower:
                    logger.warning(f"[ALLERGY] Drug '{drug_name}' is contraindicated - patient allergic to {allergen['name']}")
                    return {
                        'is_contraindicated': True,
                        'allergen_matched': allergen['name'],
                        'severity': allergen['severity'],
                        'message': f'CONTRAINDICATED: Patient has documented allergy to {allergen["name"]} (Severity: {allergen["severity"]})'
                    }
            
            return {
                'is_contraindicated': False,
                'allergen_matched': None,
                'severity': None,
                'message': f'{drug_name} is safe. No documented allergies to this drug family.'
            }
            
        except Exception as e:
            logger.error(f"[ALLERGY] Error checking drug allergy: {e}")
            return {
                'is_contraindicated': None,
                'allergen_matched': None,
                'severity': None,
                'message': f'Unable to check allergies: {str(e)}'
            }
    
    def disconnect(self):
        """Close database connection"""
        if self.db:
            self.db.disconnect()
