"""
Allergy OpenMRS Fetcher
Retrieves patient allergies from OpenMRS database
"""

import requests
from database.db import OpenMRSDatabase
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Maps food/environment allergens to excipient keywords that may appear
# in FDA inactive ingredient lists. These are standard pharmaceutical facts.
FOOD_ALLERGEN_TO_EXCIPIENT = {
    'milk':     ['lactose', 'casein', 'whey', 'lactalbumin', 'milk protein', 'milk derivative'],
    'egg':      ['egg', 'lecithin', 'lysozyme', 'albumin', 'ovalbumin'],
    'soy':      ['soy', 'soya', 'soybean', 'lecithin'],
    'peanut':   ['peanut', 'arachis'],
    'wheat':    ['wheat', 'gluten', 'starch'],
    'corn':     ['corn', 'maize', 'corn starch', 'dextrose'],
    'shellfish': ['shellfish', 'glucosamine', 'chitin'],
    'fish':     ['fish', 'cod liver', 'omega-3'],
    'gelatin':  ['gelatin', 'gelatine'],
    'latex':    ['latex', 'natural rubber'],
}


def _get_drug_classes(drug_name):
    """Fetch pharmacological class names for a drug via RxClass API.
    
    Uses the byDrugName endpoint which returns classes from multiple sources
    (ATC, VA, MeSH, etc). Filters to pharmacological class types only.
    
    Returns: list of class name strings, e.g. ["Penicillins with extended spectrum", "PENICILLINS,AMINO DERIVATIVES"]
    """
    classes = []
    try:
        resp = requests.get(
            "https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json",
            params={"drugName": drug_name},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Filter to pharmacological/chemical class types (skip disease indications)
        relevant_types = {"ATC1-4", "VA", "CHEM", "MOA", "PE", "EPC"}
        for info in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            concept = info.get("rxclassMinConceptItem", {})
            class_type = concept.get("classType", "")
            class_name = concept.get("className", "")
            if class_name and class_type in relevant_types and class_name not in classes:
                classes.append(class_name)
    except (requests.Timeout, requests.RequestException) as e:
        logger.warning(f"[ALLERGY] RxClass API timeout or request error for '{drug_name}': {e}. Using fallback.")
    except Exception as e:
        logger.debug(f"[ALLERGY] RxClass lookup failed for '{drug_name}': {e}")
    
    return classes


def _get_fda_inactive_ingredients(drug_name):
    """Fetch inactive ingredients for a drug from FDA OpenFDA API.
    
    Returns: lowercase string of all inactive ingredients, or empty string on failure.
    """
    try:
        resp = requests.get(
            "https://api.fda.gov/drug/label.json",
            params={"search": f"openfda.generic_name:{drug_name}", "limit": "1"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            ingredients = results[0].get("inactive_ingredient", [])
            return " ".join(ingredients).lower()
    except (requests.Timeout, requests.RequestException) as e:
        logger.warning(f"[ALLERGY] FDA API timeout or request error for '{drug_name}': {e}. Using fallback.")
    except Exception as e:
        logger.debug(f"[ALLERGY] FDA inactive ingredient lookup failed for '{drug_name}': {e}")
    return ""


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
        Check if a drug is contraindicated due to allergies.
        
        Four-layer matching:
        1. Direct substring match — e.g. "penicillin" ↔ "Penicillin drug class"
        2. RxNorm class cross-reactivity — e.g. "amoxicillin" → class "Penicillins"
        3. Food/Environment excipient check — e.g. patient allergic to "Milk" (FOOD),
           drug contains "lactose" as inactive ingredient → flagged
        
        Args:
            patient_id: Patient ID (external, e.g., 100008E)
            drug_name: Drug name to check (e.g., "penicillin", "amoxicillin")
        
        Returns:
            Dict with:
            - is_contraindicated: bool
            - allergen_matched: str (name of allergen if matched)
            - severity: str  
            - message: str (explanation)
            - cross_reactivity: str or None (drug class that triggered the match)
            - excipient_warning: str or None (excipient that matched a food/env allergy)
        """
        try:
            allergies = self.get_patient_allergies(patient_id)
            
            if not allergies:
                return {
                    'is_contraindicated': False,
                    'allergen_matched': None,
                    'severity': None,
                    'message': f'No allergies found for patient {patient_id}',
                    'cross_reactivity': None,
                    'excipient_warning': None
                }
            
            drug_lower = drug_name.lower()
            drug_allergies = allergies.get('DRUG', [])
            
            # --- Layer 1: Direct substring match (DRUG allergies) ---
            for allergen in drug_allergies:
                allergen_name = allergen['name'].lower() if allergen['name'] else ''
                
                if drug_lower in allergen_name or allergen_name in drug_lower:
                    logger.warning(f"[ALLERGY] Drug '{drug_name}' is contraindicated - patient allergic to {allergen['name']}")
                    return {
                        'is_contraindicated': True,
                        'allergen_matched': allergen['name'],
                        'severity': allergen['severity'],
                        'message': f'CONTRAINDICATED: Patient has documented allergy to {allergen["name"]} (Severity: {allergen["severity"]})',
                        'cross_reactivity': None,
                        'excipient_warning': None
                    }
            
            # --- Layer 2: RxNorm cross-reactivity check (DRUG allergies) ---
            drug_classes = _get_drug_classes(drug_name)
            logger.info(f"[ALLERGY] RxClass classes for '{drug_name}': {drug_classes}")
            
            if drug_classes:
                for allergen in drug_allergies:
                    allergen_name = allergen['name'].lower() if allergen['name'] else ''
                    allergen_core = allergen_name.replace('drug class', '').replace('drugs', '').strip()
                    
                    for class_name in drug_classes:
                        class_lower = class_name.lower()
                        if (allergen_core and len(allergen_core) >= 3 and 
                            (allergen_core in class_lower or class_lower in allergen_core)):
                            logger.warning(
                                f"[ALLERGY] CROSS-REACTIVITY: '{drug_name}' belongs to class '{class_name}' "
                                f"- patient has allergy to '{allergen['name']}'"
                            )
                            return {
                                'is_contraindicated': True,
                                'allergen_matched': allergen['name'],
                                'severity': allergen['severity'],
                                'message': (
                                    f'CONTRAINDICATED (Cross-Reactivity): {drug_name} belongs to the '
                                    f'{class_name} drug class. Patient has documented allergy to '
                                    f'{allergen["name"]} (Severity: {allergen["severity"]})'
                                ),
                                'cross_reactivity': class_name,
                                'excipient_warning': None
                            }
            
            # --- Layer 3: Food/Environment excipient check ---
            # Check if FOOD or ENVIRONMENT allergies conflict with drug's inactive ingredients
            food_allergies = allergies.get('FOOD', [])
            env_allergies = allergies.get('ENVIRONMENT', [])
            non_drug_allergies = food_allergies + env_allergies
            
            if non_drug_allergies:
                inactive_text = _get_fda_inactive_ingredients(drug_name)
                if inactive_text:
                    logger.info(f"[ALLERGY] Checking {len(non_drug_allergies)} food/env allergies against inactive ingredients")
                    for allergen in non_drug_allergies:
                        allergen_name = allergen['name'].lower() if allergen['name'] else ''
                        # Look up what excipients correspond to this allergen
                        for food_key, excipient_list in FOOD_ALLERGEN_TO_EXCIPIENT.items():
                            if food_key in allergen_name or allergen_name in food_key:
                                # Check if any excipient is in the inactive ingredients
                                for excipient in excipient_list:
                                    if excipient in inactive_text:
                                        logger.warning(
                                            f"[ALLERGY] EXCIPIENT WARNING: '{drug_name}' contains '{excipient}' "
                                            f"- patient has {allergen['name']} allergy"
                                        )
                                        return {
                                            'is_contraindicated': True,
                                            'allergen_matched': allergen['name'],
                                            'severity': allergen['severity'],
                                            'message': (
                                                f'CONTRAINDICATED (Excipient): {drug_name} contains {excipient} '
                                                f'as an inactive ingredient. Patient has documented allergy to '
                                                f'{allergen["name"]} (Severity: {allergen["severity"]}). '
                                                f'Use a {allergen["name"]}-free formulation or alternative medication.'
                                            ),
                                            'cross_reactivity': None,
                                            'excipient_warning': excipient
                                        }
            
            return {
                'is_contraindicated': False,
                'allergen_matched': None,
                'severity': None,
                'message': f'{drug_name} is safe. No documented allergies or cross-reactivity detected.',
                'cross_reactivity': None,
                'excipient_warning': None
            }
            
        except Exception as e:
            logger.error(f"[ALLERGY] Error checking drug allergy: {e}")
            return {
                'is_contraindicated': None,
                'allergen_matched': None,
                'severity': None,
                'message': f'Unable to check allergies: {str(e)}',
                'cross_reactivity': None,
                'excipient_warning': None
            }
    
    def check_substance_allergy(self, patient_id, substance):
        """
        Check if a patient is allergic to a specific food/substance.
        
        Checks ALL allergy types (DRUG, FOOD, ENVIRONMENT) for a match.
        Used for parent queries like "can I give egg to my child?"
        
        Args:
            patient_id: Patient ID (external, e.g., 100008E)
            substance: Substance name (e.g., "egg", "milk", "dust", "peanut")
        
        Returns:
            Dict with:
            - is_allergic: bool
            - allergen_matched: str or None
            - allergen_type: str or None (FOOD, DRUG, ENVIRONMENT)
            - severity: str or None
            - message: str
        """
        try:
            allergies = self.get_patient_allergies(patient_id)
            
            if not allergies:
                return {
                    'is_allergic': False,
                    'allergen_matched': None,
                    'allergen_type': None,
                    'severity': None,
                    'message': f'No allergies documented for patient {patient_id}.'
                }
            
            substance_lower = substance.lower()
            
            # Check all allergy types
            for allergy_type, allergen_list in allergies.items():
                for allergen in allergen_list:
                    allergen_name = allergen['name'].lower() if allergen['name'] else ''
                    if substance_lower in allergen_name or allergen_name in substance_lower:
                        logger.warning(
                            f"[ALLERGY] Substance '{substance}' matched: patient allergic to "
                            f"'{allergen['name']}' ({allergy_type})"
                        )
                        return {
                            'is_allergic': True,
                            'allergen_matched': allergen['name'],
                            'allergen_type': allergy_type,
                            'severity': allergen['severity'],
                            'message': (
                                f'WARNING: Patient has documented {allergy_type.lower()} allergy to '
                                f'{allergen["name"]} (Severity: {allergen["severity"]}). '
                                f'Do NOT give {substance} to this patient.'
                            )
                        }
            
            return {
                'is_allergic': False,
                'allergen_matched': None,
                'allergen_type': None,
                'severity': None,
                'message': f'No documented allergy to {substance}.'
            }
            
        except Exception as e:
            logger.error(f"[ALLERGY] Error checking substance allergy: {e}")
            return {
                'is_allergic': None,
                'allergen_matched': None,
                'allergen_type': None,
                'severity': None,
                'message': f'Unable to check allergies: {str(e)}'
            }
    
    def disconnect(self):
        """Close database connection"""
        if self.db:
            self.db.disconnect()
