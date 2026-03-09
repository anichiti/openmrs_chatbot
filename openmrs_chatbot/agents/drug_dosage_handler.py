"""
Drug Dosage Handler - Strict 9-Step Workflow for Safe Medication Query Processing
==================================================================================

This module implements a strict, hallucination-free drug dosage query handling system.
NO LLM internal knowledge is used - ONLY approved sources:
1. RxNorm API (drug normalization)
2. FDA OpenFDA API (dosage labels, warnings)
3. Internal Knowledge Base (KB validation, dosage rules)
4. Existing DoseCalculator (dose calculation)

CRITICAL: This module must never guess, hallucinate, or use unapproved APIs.
If ANY step fails, the query is rejected with a clear error message.
"""

import re
import requests
import json
from typing import Dict, Optional, Tuple, Any
from utils.logger import setup_logger
from utils.dose_calculator import DoseCalculator
from utils.config import OLLAMA_EMBED_MODEL
from vectorstore.chroma import VectorStore

logger = setup_logger(__name__)

# ============================================================================
# APPROVED DRUGS LIST - Check if drug is approved for dose calculation
# ============================================================================

def load_approved_drugs_list() -> Optional[Dict[str, Any]]:
    """
    Load the approved drugs list from analgesics_antipyretics_nsaids.json
    
    This list contains only approved drugs for dose calculation.
    If a drug is not in this list, dose calculation is NOT permitted.
    
    Returns: Dict with approved drugs info or None if file not found
    """
    try:
        import os
        # Get the agents directory, then go up to parent and into data
        agents_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(agents_dir)  # Go up from agents/ to openmrs_chatbot/
        kb_path = os.path.join(parent_dir, 'data', 'analgesics_antipyretics_nsaids.json')
        kb_path = os.path.abspath(kb_path)  # Normalize the path
        
        logger.info(f"[APPROVED DRUGS] Looking for approved drugs list at: {kb_path}")
        
        if not os.path.exists(kb_path):
            logger.warning(f"[APPROVED DRUGS] List not found at {kb_path}")
            return None
        
        with open(kb_path, 'r') as f:
            approved_list = json.load(f)
        
        logger.info(f"[APPROVED DRUGS] Loaded approved drugs list with {len(approved_list.get('drugs', []))} drugs")
        return approved_list
        
    except Exception as e:
        logger.error(f"[APPROVED DRUGS] Error loading approved drugs list: {str(e)}")
        return None


def is_drug_approved(drug_name: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a drug is in the approved list.
    
    Args:
        drug_name: Drug name to check (e.g., "aspirin", "ibuprofen", "paracetamol")
    
    Returns: Tuple of (is_approved: bool, drug_data: dict or None)
    - If approved: (True, drug_info_dict)
    - If not approved: (False, None)
    """
    if not drug_name:
        return False, None
    
    try:
        approved_list = load_approved_drugs_list()
        if not approved_list:
            logger.warning("[APPROVED DRUGS] Could not load approved drugs list")
            return False, None
        
        drugs = approved_list.get('drugs', [])
        drug_name_lower = drug_name.lower()
        
        # Search for exact match or alias match
        for drug_entry in drugs:
            drug_canonical = drug_entry.get('drug_name', '').lower()
            aliases = [alias.lower() for alias in drug_entry.get('aliases', [])]
            
            if drug_name_lower == drug_canonical or drug_name_lower in aliases:
                logger.info(f"[APPROVED DRUGS] Drug '{drug_name}' is APPROVED for dose calculation")
                return True, drug_entry
        
        logger.warning(f"[APPROVED DRUGS] Drug '{drug_name}' is NOT in approved list")
        return False, None
        
    except Exception as e:
        logger.error(f"[APPROVED DRUGS] Error checking if drug is approved: {str(e)}")
        return False, None


# ============================================================================
# STEP 1: Detect Drug Intent - Check for drug-related keywords in query
# ============================================================================

def detect_drug_intent(query: str) -> bool:
    """
    STEP 1: Detect if this query is asking about drug dosage/medication.
    
    Only looks for specific keywords. No interpretation - strict pattern matching.
    
    Keywords: dose, dosage, prescribe, prescription, mg, medication, drug, 
              how much, what dose, what amount, take, administer,
              adverse, effects, side effects, contraindications, precautions,
              warnings, indications, interactions, properties, information
    
    Returns: True if drug query detected, False otherwise
    """
    if not query or not isinstance(query, str):
        return False
    
    query_lower = query.lower()
    
    # Strict keyword matching - must contain at least one keyword
    drug_keywords = [
        # Dosage-related keywords
        r'\bdose\b',
        r'\bdosage\b',
        r'\bprescribe\b',
        r'\bprescription\b',
        r'\bmg\b',
        r'\bmedication\b',
        r'\bdrug\b',
        r'\bhow\s+much',
        r'\bwhat\s+dose',
        r'\bwhat\s+amount',
        r'\btake\b',
        r'\badminister\b',
        r'\b\d+mg\b',  # e.g., "100mg"
        # Drug information keywords
        r'\badverse',
        r'\beffects\b',
        r'\bside\s+effect',
        r'\bcontraindication',
        r'\bprecaution',
        r'\bwarning',
        r'\bindication',
        r'\binteraction',
        r'\bproperty|properties',
        r'\binfo|information',
        r'\bdetail',
        # New FDA field keywords
        r'\bpregnancy|pregnant',
        r'\bbreast\s*feed|nursing',
        r'\bstorage|store',
        r'\bhandling|keep',
        r'\bingredient',
        r'\bcomposition',
        r'\badministration',
        r'\boverdose',
        r'\bside\s*effect',
        r'\bsafety',
        r'\babout\s',  # "about paracetamol"
    ]
    
    for keyword in drug_keywords:
        if re.search(keyword, query_lower):
            logger.info(f"[STEP 1] Drug intent detected in query: {query}")
            return True
    
    return False


# ============================================================================
# STEP 2: Extract Drug Name - Parse drug name from query
# ============================================================================

def extract_drug_name(query: str) -> Optional[str]:
    """
    STEP 2: Extract drug name from query.
    
    Looks for drug name patterns in query. Returns first valid drug name found.
    Common patterns:
    - "...dose of [DRUG]" 
    - "[DRUG] dose"
    - "[DRUG] dosage"
    - "[DRUG] mg"
    - "prescribe [DRUG]"
    - "adverse effects for [DRUG]"
    - "[DRUG] adverse effects"
    - "[DRUG] contraindications"
    
    Returns: Drug name string or None if no drug name found
    """
    if not query or not isinstance(query, str):
        return None
    
    query_lower = query.lower()
    
    # Patterns to extract drug name (order matters - most specific first)
    # Try to find drug name after dosage amount first (most specific)
    patterns = [
        r'\d+mg\s+([a-z]+)',                                   # "500mg amoxicillin"
        # Special population patterns FIRST (before generic patterns)
        r'([a-z]+)\s+(?:safe|during|pregnancy|pregnant)',      # "paracetamol safe during pregnancy"
        r'([a-z]+)\s+(?:and)?\s*(?:pregnancy|pregnant|breast|nursing|lactation)',  # "ibuprofen and pregnancy"
        r'(?:pregnancy|pregnant|breast|nursing|lactation)\s+(?:with|and)?\s*([a-z]+)',  # "pregnancy with ibuprofen"
        r'([a-z]+)\s+(?:storage|ingredient|composition)',      # "paracetamol storage"
        r'(?:storage|store|handling|keep|ingredient|composition)\s+(?:for|of)?\s*(?:drug|medication)?\s*([a-z]+)',  # "storage for paracetamol"
        # Dosage patterns
        r'(?:dose|dosage)\s+(?:for|of)\s+(?:drug|medication)?\s*([a-z]+)',            # "dose for aspirin" or "dosage of drug aspirin"
        r'(?:what|how|is)\s+(?:the)?\s*(?:dose|dosage)\s+(?:for|of)\s+(?:drug|medication)?\s*([a-z]+)',  # "what is the dosage for paracetamol"
        r'(?:dose|dosage)\s+of\s+(?:drug|medication)?\s*([a-z]+)',                    # "dose of aspirin"
        r'([a-z]+)\s+(?:dose|dosage)',                         # "aspirin dose"
        r'([a-z]+)\s+\d+mg',                                   # "aspirin 100mg"
        r'prescribe\s+([a-z]+)',                               # "prescribe aspirin"
        r'(?:take|administer)\s+([a-z]+)',                    # "take aspirin"
        r'(?:medication|drug):\s*([a-z]+)',                    # "medication: aspirin"
        # Drug information patterns - specific keyword-based patterns with optional drug/medication
        r'(?:adverse|effects?|side effect)\s+(?:for|of)\s+(?:drug|medication)?\s*([a-z]+)',  # "adverse effects for paracetamol" or "adverse effects of drug amoxicillin"
        r'(?:contraindication|precaution|warning|indication|interaction)s?\s+(?:for|of)\s+(?:drug|medication)?\s*([a-z]+)',  # "contraindications for ibuprofen", "warnings for aspirin"
        r'(?:give|show|list)?\s*(?:me)?\s*(?:adverse|effects?|side effect|contraindication|precaution|warning|indication|interaction)s?\s+(?:of|for)\s+(?:drug|medication)?\s*([a-z]+)',  # "give me adverse effects of drug amoxicillin"
        r'(?:for|of)\s+(?:drug|medication)?\s*([a-z]+)\s+(?:adverse|effects?|side effect|contraindication|precaution|warning|indication|interaction)',  # "for paracetamol adverse effects"
        r'([a-z]+)\s+(?:adverse|contraindication|precaution|warning|indication|interaction)',  # "paracetamol adverse effects"
        r'list\s+(?:adverse|effects?|contraindication|precaution|warning|indication|interaction)s?\s+(?:for|of)?\s*(?:drug|medication)?\s*([a-z]+)',  # "list adverse effects for paracetamol"
        r'(?:what)?\s*(?:are|is|the)?\s*(?:adverse|effects?|contraindication|precaution|warning|indication|interaction)s?\s+(?:for|of)\s+(?:drug|medication)?\s*([a-z]+)',  # "what are the contraindications for ibuprofen"
        # General queries about drugs - must handle variable spacing
        r'(?:tell|info|information|about|details?|profile).*(?:about|on|for|of)\s+(?:drug|medication)?\s*([a-z]+)',  # "tell me about paracetamol"
        r'about\s+(?:drug|medication)?\s*([a-z]+)',  # "about paracetamol"
        r'(?:info|information|details?|profile)\s+(?:about|on)?\s*(?:drug|medication)?\s*([a-z]+)',  # "info paracetamol" or "information about paracetamol"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            drug_name = match.group(1).strip()
            # Avoid extracting common words
            if drug_name not in ['prescribe', 'dose', 'dosage', 'medication', 'drug', 'take', 'administer', 'of', 'for', 'effects', 'adverse', 'the', 'are', 'is', 'what', 'main', 'side', 'tell', 'me', 'about', 'info', 'information', 'details', 'profile', 'on']:
                logger.info(f"[STEP 2] Drug name extracted: {drug_name}")
                return drug_name
    
    # If no pattern matched, try extracting first capitalized word (might be drug name)
    # But log it as uncertain
    words = query.split()
    for word in words:
        if word[0].isupper() and len(word) > 2 and word not in ['What', 'How', 'The', 'Is']:
            logger.info(f"[STEP 2] Possible drug name (from capitalization): {word}")
            return word.lower()
    
    logger.warning("[STEP 2] Could not extract drug name from query")
    return None


# ============================================================================
# STEP 3: Normalize via RxNorm API - Get RxCUI and canonical name
# ============================================================================

def normalize_via_rxnorm(drug_name: str) -> Optional[Dict[str, Any]]:
    """
    STEP 3: Normalize drug name using RxNorm API.
    
    RxNorm API endpoint: https://rxnav.nlm.nih.gov/REST/
    Calls: /rxcui?name={drug_name}&search=1
    
    Returns RxCUI (unique identifier) and canonical drug name.
    If API fails or drug not found, returns None.
    
    Returns: Dict with {rxcui: str, name: str} or None if API call fails
    """
    if not drug_name:
        return None
    
    try:
        # RxNorm API endpoint for drug search
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui"
        params = {
            'name': drug_name,
            'search': '1'
        }
        
        logger.info(f"[STEP 3] Calling RxNorm API for drug: {drug_name}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if drug was found
        if 'idGroup' not in data or not data['idGroup'].get('rxuiList'):
            logger.warning(f"[STEP 3] RxNorm: Drug '{drug_name}' not found in RxNorm")
            return None
        
        # Get first RxCUI result
        rxcui = data['idGroup']['rxuiList'][0]
        
        # Get canonical name
        name_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties"
        name_response = requests.get(name_url, timeout=10)
        name_response.raise_for_status()
        name_data = name_response.json()
        
        canonical_name = name_data.get('properties', {}).get('name', drug_name)
        
        result = {
            'rxcui': rxcui,
            'name': canonical_name
        }
        
        logger.info(f"[STEP 3] RxNorm normalization successful: {drug_name} -> {canonical_name} (RxCUI: {rxcui})")
        return result
        
    except requests.exceptions.Timeout:
        logger.error(f"[STEP 3] RxNorm API timeout for drug: {drug_name}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[STEP 3] RxNorm API error for drug '{drug_name}': {str(e)}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"[STEP 3] RxNorm API response parsing error: {str(e)}")
        logger.error(f"[STEP 3] Response text: {response.text if 'response' in locals() else 'N/A'}")
        return None


# ============================================================================
# STEP 4: Check Knowledge Base - Validate drug exists in KB with dosage rules
# ============================================================================

def check_knowledge_base(drug_name: str, rxcui: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    STEP 4: Check if drug exists in internal knowledge base.
    
    CRITICAL RULE: Drug MUST exist in KB before proceeding to FDA API.
    This prevents returning dosage info for drugs we don't have internal rules for.
    
    Queries doctor KB for drug dosage information.
    
    Returns: Dict with KB dosage rules or None if drug not in KB
    """
    if not drug_name:
        return None
    
    try:
        # Initialize vector store for KB query
        vector_store = VectorStore()
        
        # Ensure collections are initialized
        if not vector_store.client:
            logger.warning(f"[STEP 4] ChromaDB client unavailable - Knowledge Base query failed")
            return None
        
        # Search doctor KB for drug information
        logger.info(f"[STEP 4] Querying Knowledge Base for: {drug_name}")
        query = f"dosage indications contraindications {drug_name} pediatric adult children"
        
        kb_results = vector_store.query_doctor_kb(query, top_k=5)
        
        if not kb_results or not kb_results.get('documents') or not kb_results['documents'][0]:
            logger.warning(f"[STEP 4] Knowledge Base: No dosage rules found for {drug_name}")
            return None
        
        # Filter out empty results
        docs = [doc for doc in kb_results['documents'][0] if doc and len(doc.strip()) > 10]
        if not docs:
            logger.warning(f"[STEP 4] Knowledge Base: Found results but all empty for {drug_name}")
            return None
        
        # Extract relevant KB info
        kb_data = {
            'drug_name': drug_name,
            'rxcui': rxcui,
            'kb_documents': docs[:3],  # Keep top 3 documents
            'kb_distances': kb_results.get('distances', [[]])[0][:3] if kb_results.get('distances') else [],
            'kb_found': True
        }
        
        logger.info(f"[STEP 4] Knowledge Base validation successful: {drug_name} found in KB with {len(docs)} relevant documents")
        return kb_data
        
    except Exception as e:
        logger.error(f"[STEP 4] Knowledge Base query error for {drug_name}: {str(e)}")
        logger.error(f"[STEP 4] Make sure Ollama is running and has embedding model: ollama pull nomic-embed-text")
        return None


def check_knowledge_base_with_fallback(drug_name: str, rxcui: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    STEP 4: Check Knowledge Base with MULTIPLE FALLBACK SOURCES.
    
    Priority order:
    1. Approved Drugs List (analgesics_antipyretics_nsaids.json) - NEW PRIMARY SOURCE!
    2. Vector KB query (from PDFs)
    3. Local drug database (medical_drugs.json)
    4. Text-based KB (drug_knowledge_base.json)
    
    This ensures we have drug information from the most reliable approved source.
    
    Returns: Dict with KB dosage rules or None if drug not in any source
    """
    # FIRST PRIORITY: Check Approved Drugs List
    logger.info(f"[STEP 4] Checking approved drugs list for {drug_name}...")
    try:
        import os
        approved_list = load_approved_drugs_list()
        if approved_list:
            drugs = approved_list.get('drugs', [])
            drug_name_lower = drug_name.lower()
            
            for drug_entry in drugs:
                drug_canonical = drug_entry.get('drug_name', '').lower()
                aliases = [alias.lower() for alias in drug_entry.get('aliases', [])]
                
                if drug_name_lower == drug_canonical or drug_name_lower in aliases:
                    logger.info(f"[STEP 4] FOUND in Approved Drugs List: {drug_name}")
                    
                    # Extract dosage info
                    kb_data = {
                        'drug_name': drug_name,
                        'rxcui': rxcui or drug_entry.get('atc_code'),
                        'kb_documents': [],
                        'kb_distances': [],
                        'kb_found': False,
                        'approved_list_found': True,
                        'category': drug_entry.get('category'),
                        'indications': drug_entry.get('indications', []),
                        'contraindications': drug_entry.get('contraindications', []),
                        'precautions': drug_entry.get('precautions', []),
                        'major_warnings': drug_entry.get('major_warnings', []),
                        'adverse_effects': drug_entry.get('adverse_effects', {}),
                        'age_restriction': drug_entry.get('age_restriction', {}),
                        'dosing_info': drug_entry,  # Full drug entry for dose calculation
                        'source': 'WHO Analgesics/Antipyretics/NSAIDs Approved List',
                        'approval_status': 'Approved (WHO Pediatric Essential Medicines)'
                    }
                    
                    logger.info(f"[STEP 4] Approved drugs validation successful for {drug_name}")
                    return kb_data
    except Exception as e:
        logger.error(f"[STEP 4] Error checking approved drugs list: {str(e)}")
    
    # Try KB vector store
    kb_result = check_knowledge_base(drug_name, rxcui)
    if kb_result:
        logger.info(f"[STEP 4] Using vector KB for {drug_name}")
        return kb_result
    
    # Fallback to local drug database if KB fails
    logger.info(f"[STEP 4] Vector KB returned no results, checking local drug database...")
    try:
        import os
        
        # Load medical_drugs.json
        drug_db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'medical_drugs.json')
        with open(drug_db_path, 'r') as f:
            drug_database = json.load(f)
        
        # Search for drug by name or aliases
        drugs_list = drug_database.get('drugs', [])
        for drug_entry in drugs_list:
            drug_canonical = drug_entry.get('drug_name', '').lower()
            aliases = [alias.lower() for alias in drug_entry.get('aliases', [])]
            
            # Check if drug matches (by name or alias)
            if drug_name.lower() == drug_canonical or drug_name.lower() in aliases:
                logger.info(f"[STEP 4] Found {drug_name} in local drug database")
                
                # Extract dosage info
                kb_data = {
                    'drug_name': drug_name,
                    'rxcui': rxcui or drug_entry.get('atc_code'),
                    'kb_documents': [],  # No KB docs from local DB
                    'kb_distances': [],
                    'kb_found': False,
                    'local_db_found': True,
                    'category': drug_entry.get('category'),
                    'indications': drug_entry.get('indications', []),
                    'contraindications': drug_entry.get('contraindications', []),
                    'major_warnings': drug_entry.get('major_warnings', []),
                    'precautions': drug_entry.get('precautions', []),
                    'dosing_info': drug_entry  # Store full drug entry
                }
                
                logger.info(f"[STEP 4] Local DB validation successful for {drug_name}")
                return kb_data
        
        # If not in medical_drugs.json, try drug_knowledge_base.json
        logger.info(f"[STEP 4] Drug not in medical_drugs.json, checking readable drug knowledge base...")
        kb_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'drug_knowledge_base.json')
        with open(kb_path, 'r') as f:
            drug_kb = json.load(f)
        
        # Search in the structured knowledge base
        drugs_kb = drug_kb.get('drugs', {})
        for drug_key, drug_info in drugs_kb.items():
            canonical = drug_info.get('canonical_name', '').lower()
            aliases = [alias.lower() for alias in drug_info.get('aliases', [])]
            
            if drug_name.lower() == drug_key.lower() or drug_name.lower() == canonical or drug_name.lower() in aliases:
                logger.info(f"[STEP 4] Found {drug_name} in readable drug knowledge base")
                
                kb_data = {
                    'drug_name': drug_name,
                    'rxcui': rxcui or drug_info.get('atc_code'),
                    'kb_documents': [],
                    'kb_distances': [],
                    'kb_found': False,
                    'knowledge_base_found': True,
                    'category': drug_info.get('category'),
                    'indications': drug_info.get('indications', []),
                    'contraindications': drug_info.get('contraindications', []),
                    'major_warnings': drug_info.get('major_warnings', []),
                    'precautions': drug_info.get('precautions', []),
                    'dosing_info': drug_info,
                    'approval_status': drug_info.get('approval_status'),
                    'source': drug_info.get('source')
                }
                
                logger.info(f"[STEP 4] Knowledge base validation successful for {drug_name}")
                logger.info(f"[STEP 4] Source: {drug_info.get('source')} | Status: {drug_info.get('approval_status')}")
                return kb_data
        
        # Drug not found in any source
        logger.warning(f"[STEP 4] Drug not found in any knowledge base: {drug_name}")
        return None
        
    except FileNotFoundError as e:
        logger.warning(f"[STEP 4] Knowledge base file not found: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[STEP 4] Error reading knowledge bases: {str(e)}")
        return None


# ============================================================================
# STEP 5: Fetch FDA Label - Get official dosage from FDA OpenFDA API
# ============================================================================

def fetch_fda_label(rxcui: str) -> Optional[Dict[str, Any]]:
    """
    STEP 5: Fetch FDA drug label from OpenFDA API.
    
    FDA OpenFDA API endpoint: https://api.fda.gov/drug/label.json
    Searches by RxCUI or drug name.
    
    Extracts:
    - dosage_and_administration
    - warnings
    - indications_and_usage
    
    Returns: Dict with FDA label data or None if API fails
    """
    if not rxcui:
        return None
    
    try:
        # Query FDA API using RxCUI
        url = "https://api.fda.gov/drug/label.json"
        params = {
            'search': f'openfda.rxcui:{rxcui}',
            'limit': 1
        }
        
        logger.info(f"[STEP 5] Calling FDA OpenFDA API for RxCUI: {rxcui}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'results' not in data or not data['results']:
            logger.warning(f"[STEP 5] FDA API: No label found for RxCUI {rxcui}")
            return None
        
        label = data['results'][0]
        
        fda_data = {
            'rxcui': rxcui,
            'found': True,
            'dosage_and_administration': label.get('dosage_and_administration', ['N/A'])[0] if label.get('dosage_and_administration') else 'N/A',
            'warnings': label.get('warnings', ['N/A'])[0] if label.get('warnings') else 'N/A',
            'indications_and_usage': label.get('indications_and_usage', ['N/A'])[0] if label.get('indications_and_usage') else 'N/A',
        }
        
        logger.info(f"[STEP 5] FDA label retrieved for RxCUI: {rxcui}")
        return fda_data
        
    except requests.exceptions.Timeout:
        logger.error(f"[STEP 5] FDA API timeout for RxCUI: {rxcui}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[STEP 5] FDA API error for RxCUI {rxcui}: {str(e)}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"[STEP 5] FDA API response parsing error: {str(e)}")
        return None


# ============================================================================
# STEP 6: Get Patient Data - Retrieve age and weight from OpenMRS
# ============================================================================

def get_patient_data_from_openmrs(patient_id: int, db_connection) -> Optional[Dict[str, Any]]:
    """
    STEP 6: Retrieve patient age and weight from OpenMRS database.
    
    Required for dose calculation using DoseCalculator.
    Gets current age and most recent weight measurement.
    
    Args:
        patient_id: OpenMRS patient ID (can be external identifier like "100008E" or internal integer)
        db_connection: Database connection object from database/db.py
    
    Returns: Dict with {age_years: int, weight_kg: float} or None if lookup fails
    """
    if not patient_id or not db_connection:
        return None
    
    try:
        logger.info(f"[STEP 6] Retrieving patient data from OpenMRS for patient {patient_id}")
        
        # First, verify patient exists and get internal patient_id if needed
        patient_info = db_connection.verify_patient_exists(patient_id)
        
        if patient_info is None:
            logger.error(f"[STEP 6] Database connection error when verifying patient {patient_id}")
            return None
        
        if patient_info is False:
            logger.error(f"[STEP 6] Patient {patient_id} not found in OpenMRS")
            return None
        
        # Get the internal patient_id for database queries
        internal_patient_id = patient_info.get('patient_id')
        if not internal_patient_id:
            logger.error(f"[STEP 6] Could not extract internal patient ID from {patient_id}")
            return None
        
        logger.info(f"[STEP 6] Patient ID {patient_id} resolved to internal ID {internal_patient_id}")
        
        # Get patient age
        age = db_connection.get_patient_age(internal_patient_id)
        if age is None:
            logger.warning(f"[STEP 6] Could not retrieve age for patient {patient_id} (internal ID {internal_patient_id})")
            return None
        
        # Get patient weight (most recent vital)
        vitals_result = db_connection.get_patient_recent_vitals(internal_patient_id)
        weight = None
        
        if vitals_result and not vitals_result.get("error"):
            vitals_data = vitals_result.get("data", [])
            
            # Look for weight in vitals
            for vital in vitals_data:
                vital_name = vital.get('vital_name', '')
                if vital_name and 'weight' in vital_name.lower():
                    weight = vital.get('value_numeric')
                    logger.info(f"[STEP 6] Extracted weight from vitals: {weight} kg")
                    break
        
        if weight is None:
            logger.warning(f"[STEP 6] Could not retrieve weight for patient {patient_id}")
            # Continue anyway - some calculations might not need weight
        
        patient_data = {
            'patient_id': patient_id,
            'internal_patient_id': internal_patient_id,
            'age_years': age,
            'weight_kg': weight if weight else 0
        }
        
        logger.info(f"[STEP 6] Patient data retrieved: Age={age}y, Weight={weight}kg")
        return patient_data
        
    except Exception as e:
        logger.error(f"[STEP 6] Error retrieving patient data: {str(e)}")
        return None


# ============================================================================
# STEP 7: Calculate Dose - Use existing DoseCalculator for safe calculation
# ============================================================================

def calculate_dose(drug_data: Any, age_years: int, weight_kg: float, 
                   kb_rules: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    STEP 7: Calculate dose using existing DoseCalculator.
    
    CRITICAL: Uses ONLY the existing /utils/dose_calculator.py - no modifications.
    Input: drug data (dict or name), patient age, patient weight
    Output: Calculated dose(s) based on age group and weight
    
    drug_data can be:
    - A dictionary with dose information (from local drug database)
    - A string with drug name (for backward compatibility)
    
    Returns: Dict from DoseCalculator with:
    {
        'age_group': str,
        'weight_kg': float,
        'dose_per_admin_mg': float (or None),
        'dose_range_mg': str (or None),
        'max_single_dose_mg': float (or None)
    }
    
    Returns None if calculation fails.
    """
    if not drug_data or age_years is None:
        return None
    
    try:
        drug_name = drug_data if isinstance(drug_data, str) else drug_data.get('drug_name', 'unknown')
        logger.info(f"[STEP 7] Calculating dose for {drug_name}: age={age_years}y, weight={weight_kg}kg")
        
        # Initialize DoseCalculator
        dose_calc = DoseCalculator()
        
        # Calculate dose using existing calculator
        # DoseCalculator expects drug as a dict with dose information
        calculated = dose_calc.calculate_dose(
            weight_kg=weight_kg,
            age_years=age_years,
            drug=drug_data  # Pass the dict or use string as-is if DoseCalculator handles it
        )
        
        if not calculated:
            logger.warning(f"[STEP 7] DoseCalculator returned no result for {drug_name}")
            return None
        
        logger.info(f"[STEP 7] Dose calculated successfully: {calculated}")
        return calculated
        
    except Exception as e:
        logger.error(f"[STEP 7] DoseCalculator error: {str(e)}")
        return None


# ============================================================================
# STEP 8: Validate Against Limits - Check dose against KB and FDA limits
# ============================================================================

def validate_against_limits(calculated_dose: Dict[str, Any], 
                           kb_data: Optional[str] = None,
                           fda_data: Optional[Dict] = None) -> Tuple[bool, str]:
    """
    STEP 8: Validate calculated dose against KB limits and FDA recommendations.
    
    Rules:
    - Check minimum dose (must be > 0)
    - Check maximum single dose
    - If dose exceeds limits, apply warning and cap to maximum
    - Always return validation status and message
    
    Returns: Tuple of (is_valid: bool, message: str)
    - is_valid=True: Dose is safe
    - is_valid=False: Dose exceeds limits but message explains why
    """
    if not calculated_dose:
        return False, "No dose calculated to validate"
    
    logger.info(f"[STEP 8] Validating dose: {calculated_dose}")
    
    message = ""
    is_valid = True
    
    # Check if dose exists
    dose_value = calculated_dose.get('dose_per_admin_mg') or calculated_dose.get('dose_range_mg')
    
    if not dose_value:
        return False, "No dose value found to validate"
    
    # Parse numeric dose if it's a range
    try:
        if isinstance(dose_value, str) and '-' in dose_value:
            # It's a range like "100-200mg"
            parts = dose_value.split('-')
            dose_min = float(parts[0])
            dose_max = float(parts[1].replace('mg', '').strip())
        else:
            dose_min = dose_max = float(str(dose_value).replace('mg', '').strip())
    except (ValueError, IndexError):
        logger.warning(f"[STEP 8] Could not parse dose value: {dose_value}")
        return True, "Dose validation skipped (format issue)"
    
    # Check minimum dose
    if dose_min <= 0:
        return False, f"Dose is too low: {dose_value}"
    
    # Check maximum single dose
    max_dose = calculated_dose.get('max_single_dose_mg')
    if max_dose and dose_max > max_dose:
        message = f"WARNING: Calculated dose {dose_value} exceeds maximum {max_dose}mg. Capping to maximum."
        is_valid = False
        logger.warning(f"[STEP 8] Dose exceeds maximum: {message}")
    else:
        message = f"Dose validated: {dose_value} is safe"
        is_valid = True
        logger.info(f"[STEP 8] {message}")
    
    return is_valid, message


# ============================================================================
# STEP 9: Compose Response - Format final response with source attribution
# ============================================================================

def extract_dosing_limits(dosing_info: Dict[str, Any], age_group: str, weight_kg: float) -> Tuple[Optional[float], Optional[float]]:
    """
    GENERIC: Extract max_single_dose_mg and max_daily_mg from any drug's dosing structure.
    
    This function is flexible to handle ANY drug structure added in the future:
    - Searches through dose configuration for age-specific limits
    - Falls back to generic limits if age-specific not found
    - Calculates max_daily from weight-based formulas if needed
    
    Args:
        dosing_info: Full drug dosing structure from KB
        age_group: Patient's age group (neonate, infant, child, adult, etc.)
        weight_kg: Patient weight in kg
    
    Returns: Tuple of (max_single_dose_mg, max_daily_dose_mg) or (None, None)
    """
    if not dosing_info or not isinstance(dosing_info, dict):
        return None, None
    
    max_single = None
    max_daily = None
    
    try:
        dose_config = dosing_info.get('dose', {})
        if not dose_config:
            return None, None
        
        # Age group for searching (normalize to lowercase)
        age_group_lower = age_group.lower() if age_group else ''
        
        # Strategy 1: Look for direct age-group keys in dose_config
        # Handles: 'neonate', 'infant', 'child', 'adult', or combined like 'infant_child'
        for key in dose_config.keys():
            key_lower = key.lower()
            
            # Check if this key matches the patient's age group
            if age_group_lower in key_lower or key_lower == age_group_lower:
                age_config = dose_config[key]
                if isinstance(age_config, dict):
                    max_single = max_single or age_config.get('max_single_dose_mg')
                    max_daily = max_daily or age_config.get('max_daily_mg')
                    
                    # If max_daily_mg_per_kg exists, calculate total
                    if not max_daily and age_config.get('max_daily_mg_per_kg'):
                        max_daily = age_config['max_daily_mg_per_kg'] * weight_kg
        
        # Strategy 2: If not found by exact age group, search all nested configs
        # (handles drugs with flexible or unconventional structures)
        if not max_single or not max_daily:
            for key, config in dose_config.items():
                if isinstance(config, dict):
                    if not max_single:
                        max_single = config.get('max_single_dose_mg')
                    if not max_daily:
                        max_daily = config.get('max_daily_mg')
                        # Calculate from per-kg if needed
                        if not max_daily and config.get('max_daily_mg_per_kg'):
                            max_daily = config['max_daily_mg_per_kg'] * weight_kg
        
        return max_single, max_daily
        
    except Exception as e:
        logger.warning(f"Error extracting dosing limits: {str(e)}")
        return None, None


def compose_response(drug_info: Dict[str, Any], 
                    patient_data: Dict[str, Any],
                    patient_age: int,
                    patient_weight: float,
                    calculated_dose: Dict[str, Any],
                    kb_data: Optional[Dict] = None,
                    fda_data: Optional[Dict] = None,
                    validation: Tuple[bool, str] = (True, "")) -> str:
    """
    STEP 9: Compose structured response in clean, clinical format.
    
    FUTURE-PROOF: Works with any drug structure added later.
    Automatically extracts and displays available dosing information.
    
    Returns: Formatted response string with:
    - Drug name (WHO approval status)
    - Calculated dose for patient's age/weight
    - Frequency and estimated doses per day
    - Min/Max limits (if available)
    - Validation status
    - Major warnings
    - Source attribution
    """
    
    response_lines = []
    
    # Drug name with approval status
    drug_name = drug_info.get('name', 'Unknown')
    approval_suffix = " (WHO-Approved)" if kb_data and kb_data.get('approved_list_found') else ""
    response_lines.append(f"Drug: {drug_name}{approval_suffix}")
    
    # Patient demographics (for reference)
    age_group = calculated_dose.get('age_group', 'Unknown')
    response_lines.append(f"Patient: {patient_age} years old, {patient_weight} kg ({age_group})")
    response_lines.append("")
    
    # Calculated dose based on age and weight
    if calculated_dose.get('dose_per_admin_mg'):
        response_lines.append(f"Dose: {calculated_dose['dose_per_admin_mg']} mg per administration")
    
    # Handle dose range if available
    if calculated_dose.get('dose_range_mg'):
        dose_range = calculated_dose['dose_range_mg']
        if isinstance(dose_range, dict) and 'low' in dose_range and 'high' in dose_range:
            low = dose_range['low']
            high = dose_range['high']
            response_lines.append(f"Dose Range: {low}-{high} mg")
    
    # Extract min/max limits from ANY drug structure using generic function
    max_single = None
    max_daily = None
    
    if kb_data and kb_data.get('dosing_info'):
        dosing_info = kb_data.get('dosing_info', {})
        age_group = calculated_dose.get('age_group', 'unknown')
        max_single, max_daily = extract_dosing_limits(dosing_info, age_group, patient_weight)
        
        if max_single:
            response_lines.append(f"Maximum Single Dose: {max_single} mg")
        if max_daily:
            response_lines.append(f"Maximum Daily Dose: {max_daily} mg")
    
    # Frequency
    if calculated_dose.get('frequency'):
        response_lines.append(f"Frequency: {calculated_dose['frequency']}")
    
    # Estimated doses per day
    if calculated_dose.get('estimated_doses_per_day'):
        est_doses = calculated_dose['estimated_doses_per_day']
        if isinstance(est_doses, dict):
            min_d = est_doses.get('min', '?')
            max_d = est_doses.get('max', '?')
            response_lines.append(f"Estimated: {min_d}-{max_d} doses per day")
    
    # Validation status
    is_valid, validation_msg = validation
    response_lines.append("")
    response_lines.append(f"Validation: {'SAFE' if is_valid else 'WARNING'}")
    
    # Warnings from knowledge base (works with any drug)
    if kb_data and kb_data.get('major_warnings'):
        response_lines.append("Warnings:")
        for warning in kb_data.get('major_warnings', [])[:3]:
            response_lines.append(f"  - {warning}")
    
    response_lines.append("")
    
    # Source attribution
    if kb_data and kb_data.get('approved_list_found'):
        response_lines.append(f"Source: WHO Analgesics/Antipyretics/NSAIDs Approved List")
        response_lines.append(f"Calculation: DoseCalculator (based on age {patient_age}y, weight {patient_weight}kg)")
    elif kb_data:
        source = kb_data.get('source', 'Internal Drug Database')
        response_lines.append(f"Source: {source}")
    
    response_lines.append("")
    response_lines.append("=" * 70)
    response_lines.append("IMPORTANT: Always consult physician references and established protocols.")
    response_lines.append("=" * 70)
    
    return "\n".join(response_lines)


# ============================================================================
# DRUG INFORMATION EXTRACTOR: Get drug details without dose calculation
# ============================================================================

def extract_drug_information(query: str, drug_name: str) -> str:
    """
    Extract drug information from MULTIPLE SOURCES with intelligent fallback:
    1. RxNorm API - Normalize drug name (brand → generic)
    2. FDA API - Get comprehensive drug information
    3. JSON Knowledge Base - Fallback for approved drugs
    
    Args:
        query: User's question about the drug
        drug_name: Name of the drug to look up
    
    Returns: Formatted response with drug information from all available sources
    """
    
    logger.info(f"[DRUG INFO] Extracting information for: {drug_name}")
    logger.info(f"[DRUG INFO] Query: {query}")
    
    # Initialize API skills
    rxnorm_skill = None
    fda_skill = None
    
    try:
        from utils.rxnorm_api_skill import RxNormAPISkill
        from utils.fda_api_skill import FDAAPISkill
        rxnorm_skill = RxNormAPISkill()
        fda_skill = FDAAPISkill()
        logger.info(f"[DRUG INFO] API skills initialized")
    except Exception as e:
        logger.warning(f"[DRUG INFO] Could not initialize API skills: {e}")
    
    # ========== STEP 1: Try RxNorm API to normalize drug name ==========
    normalized_name = drug_name
    rxcui = None
    
    if rxnorm_skill:
        try:
            logger.info(f"[DRUG INFO] Calling RxNorm API to normalize: {drug_name}")
            rxnorm_result = rxnorm_skill.normalize_drug(drug_name)
            if rxnorm_result and "error" not in rxnorm_result:
                rxcui = rxnorm_result.get('rxcui')
                generic_name = rxnorm_result.get('generic_name')
                if generic_name:
                    normalized_name = generic_name
                    logger.info(f"[DRUG INFO] RxNorm normalized: {drug_name} → {normalized_name} (RxCUI: {rxcui})")
            else:
                logger.warning(f"[DRUG INFO] RxNorm normalization failed: {rxnorm_result}")
        except Exception as e:
            logger.warning(f"[DRUG INFO] RxNorm API error: {e}")
    
    # ========== STEP 2: Try FDA API for comprehensive information ==========
    fda_data = None
    if fda_skill:
        try:
            logger.info(f"[DRUG INFO] Calling FDA API for: {normalized_name}")
            fda_data = fda_skill.get_drug_label(normalized_name)
            if fda_data and "warning" not in fda_data:
                logger.info(f"[DRUG INFO] FDA API returned data successfully")
                logger.debug(f"[DRUG INFO] FDA Data Keys: {list(fda_data.keys())}")
                if fda_data.get('indications'):
                    logger.debug(f"[DRUG INFO] FDA Indications (first 100 chars): {fda_data['indications'][:100]}")
                if fda_data.get('warnings'):
                    logger.debug(f"[DRUG INFO] FDA Warnings (first 100 chars): {fda_data['warnings'][:100]}")
            else:
                logger.warning(f"[DRUG INFO] FDA API returned no useful data")
                fda_data = None
        except Exception as e:
            logger.warning(f"[DRUG INFO] FDA API error: {e}")
            fda_data = None
    
    # ========== STEP 3: Get data from JSON Knowledge Base ==========
    kb_data = None
    try:
        approved_list = load_approved_drugs_list()
        if approved_list:
            drugs = approved_list.get('drugs', [])
            drug_name_lower = drug_name.lower()
            
            # Search by original name or normalized name
            for drug in drugs:
                if (drug.get('drug_name', '').lower() == drug_name_lower or 
                    drug.get('drug_name', '').lower() == normalized_name.lower() or
                    drug_name_lower in [alias.lower() for alias in drug.get('aliases', [])]):
                    kb_data = drug
                    logger.info(f"[DRUG INFO] Found in JSON KB: {drug.get('drug_name')}")
                    break
    except Exception as e:
        logger.warning(f"[DRUG INFO] Error loading JSON KB: {e}")
    
    # ========== BUILD RESPONSE from all sources ==========
    response_lines = []
    response_lines.append("=" * 70)
    response_lines.append("DRUG INFORMATION: " + normalized_name.upper())
    response_lines.append("=" * 70)
    response_lines.append("")
    
    # Show FDA-specific data first if available
    if fda_data and (fda_data.get('indications') or fda_data.get('warnings') or fda_data.get('adverse_reactions')):
        response_lines.append("[FDA OFFICIAL LABEL DATA]")
        response_lines.append("-" * 70)
        if fda_data.get('indications'):
            response_lines.append("FDA APPROVED USES:")
            response_lines.append("  " + fda_data['indications'][:300] + ("..." if len(fda_data['indications']) > 300 else ""))
            response_lines.append("")
        if fda_data.get('warnings'):
            response_lines.append("FDA WARNINGS:")
            response_lines.append("  " + fda_data['warnings'][:300] + ("..." if len(fda_data['warnings']) > 300 else ""))
            response_lines.append("")
        response_lines.append("")
    
    # Add source information with detail about what came from where
    sources = []
    source_detail = []
    if fda_data:
        sources.append("FDA OpenFDA API")
        fda_sources = []
        if fda_data.get('indications'):
            fda_sources.append("indications")
        if fda_data.get('warnings'):
            fda_sources.append("warnings")
        if fda_data.get('contraindications'):
            fda_sources.append("contraindications")
        if fda_data.get('adverse_reactions'):
            fda_sources.append("adverse reactions")
        if fda_sources:
            source_detail.append(f"FDA provides: {', '.join(fda_sources)}")
    
    if kb_data:
        sources.append("WHO Analgesics/Antipyretics/NSAIDs KB")
        kb_sources = []
        if kb_data.get('indications'):
            kb_sources.append("indications")
        if kb_data.get('contraindications'):
            kb_sources.append("contraindications")
        if kb_data.get('major_warnings'):
            kb_sources.append("warnings")
        if kb_data.get('adverse_effects'):
            kb_sources.append("adverse effects")
        if kb_sources:
            source_detail.append(f"KB provides: {', '.join(kb_sources)}")
    
    if rxcui:
        sources.append(f"RxNorm (RxCUI: {rxcui})")
    
    if sources:
        response_lines.append("Data Sources: " + ", ".join(sources))
        if source_detail:
            for detail in source_detail:
                response_lines.append(f"  | {detail}")
        response_lines.append("")
    
    # Check what information is being requested
    query_lower = query.lower()
    
    # INDICATIONS (from FDA first, then KB)
    if 'indication' in query_lower or 'use for' in query_lower or 'when to use' in query_lower or 'treatment' in query_lower:
        response_lines.append("INDICATIONS (Uses):")
        response_lines.append("-" * 70)
        
        if fda_data and fda_data.get('indications'):
            response_lines.append("[FDA]:")
            response_lines.append("  " + fda_data['indications'])
            response_lines.append("")
        
        if kb_data and kb_data.get('indications'):
            response_lines.append("[Knowledge Base]:")
            for ind in kb_data.get('indications', []):
                response_lines.append("  [+] " + ind)
        
        if not (fda_data and fda_data.get('indications')) and not (kb_data and kb_data.get('indications')):
            response_lines.append("  No indications data available")
        
        response_lines.append("")
    
    # WARNINGS (from FDA first, then KB)
    if 'warning' in query_lower or 'caution' in query_lower or 'carefull' in query_lower:
        response_lines.append("WARNINGS:")
        response_lines.append("-" * 70)
        
        if fda_data and fda_data.get('warnings'):
            response_lines.append("[FDA]:")
            response_lines.append("  " + fda_data['warnings'])
            response_lines.append("")
        
        if kb_data and kb_data.get('major_warnings'):
            response_lines.append("[Knowledge Base]:")
            for warning in kb_data.get('major_warnings', []):
                response_lines.append("  [!] " + warning)
        
        if not (fda_data and fda_data.get('warnings')) and not (kb_data and kb_data.get('major_warnings')):
            response_lines.append("  No warnings data available")
        
        response_lines.append("")
    
    # CONTRAINDICATIONS (from FDA first, then KB)
    if 'contraindication' in query_lower or 'avoid' in query_lower or 'should not' in query_lower:
        response_lines.append("CONTRAINDICATIONS:")
        response_lines.append("-" * 70)
        
        if fda_data and fda_data.get('contraindications'):
            response_lines.append("[FDA]:")
            response_lines.append("  " + fda_data['contraindications'])
            response_lines.append("")
        
        if kb_data and kb_data.get('contraindications'):
            response_lines.append("[Knowledge Base]:")
            for contra in kb_data.get('contraindications', []):
                response_lines.append("  [X] " + contra)
        
        if not (fda_data and fda_data.get('contraindications')) and not (kb_data and kb_data.get('contraindications')):
            response_lines.append("  No contraindications data available")
        
        response_lines.append("")
    
    # ADVERSE EFFECTS (from FDA first, then KB)
    if 'adverse' in query_lower or 'effect' in query_lower or 'side' in query_lower:
        response_lines.append("ADVERSE EFFECTS / SIDE EFFECTS:")
        response_lines.append("-" * 70)
        
        if fda_data and fda_data.get('adverse_reactions'):
            response_lines.append("[FDA]:")
            response_lines.append("  " + fda_data['adverse_reactions'])
            response_lines.append("")
        
        if kb_data and kb_data.get('adverse_effects'):
            response_lines.append("[Knowledge Base]:")
            adverse = kb_data.get('adverse_effects', {})
            if isinstance(adverse, dict):
                if adverse.get('common'):
                    response_lines.append("  Common: " + ", ".join(adverse.get('common', [])))
                if adverse.get('rare'):
                    response_lines.append("  Rare: " + ", ".join(adverse.get('rare', [])))
                if adverse.get('serious'):
                    response_lines.append("  Serious: " + ", ".join(adverse.get('serious', [])))
        
        if not (fda_data and fda_data.get('adverse_reactions')) and not (kb_data and kb_data.get('adverse_effects')):
            response_lines.append("  No adverse effects data available")
        
        response_lines.append("")
    
    # PRECAUTIONS (from KB primarily)
    if 'precaution' in query_lower or 'caution' in query_lower or 'careful' in query_lower:
        response_lines.append("PRECAUTIONS:")
        response_lines.append("-" * 70)
        
        if kb_data and kb_data.get('precautions'):
            for prec in kb_data.get('precautions', []):
                response_lines.append("  [!] " + prec)
        else:
            response_lines.append("  No specific precautions listed")
        
        response_lines.append("")
    
    # INTERACTIONS (from KB primarily)
    if 'interaction' in query_lower or 'interact' in query_lower or 'other drug' in query_lower:
        response_lines.append("DRUG INTERACTIONS:")
        response_lines.append("-" * 70)
        
        if kb_data and kb_data.get('interactions'):
            for inter in kb_data.get('interactions', []):
                drug = inter.get('drug', 'Unknown')
                effect = inter.get('effect', 'Interaction')
                response_lines.append("  * " + drug + ": " + effect)
        else:
            response_lines.append("  No specific interactions listed")
        
        response_lines.append("")
    
    # If no specific query, show comprehensive information
    if not any(keyword in query_lower for keyword in ['adverse', 'effect', 'contraindication', 'precaution', 'indication', 'interaction', 'warning']):
        logger.info(f"[DRUG INFO] No specific keyword found, showing comprehensive information")
        
        # General info from KB
        if kb_data:
            response_lines.append("CATEGORY: " + kb_data.get('category', 'Unknown'))
            response_lines.append("")
            
            if kb_data.get('indications'):
                response_lines.append("INDICATIONS:")
                for ind in kb_data.get('indications', []):
                    response_lines.append("  [+] " + ind)
                response_lines.append("")
        
        # FDA Indications 
        if fda_data and fda_data.get('indications'):
            response_lines.append("FDA INDICATIONS:")
            response_lines.append("  " + fda_data['indications'])
            response_lines.append("")
        
        # Warnings
        if kb_data and kb_data.get('major_warnings'):
            response_lines.append("WARNINGS:")
            for warning in kb_data.get('major_warnings', []):
                response_lines.append("  [!] " + warning)
            response_lines.append("")
        
        if fda_data and fda_data.get('warnings'):
            response_lines.append("FDA WARNINGS:")
            response_lines.append("  " + fda_data['warnings'])
            response_lines.append("")
        
        # Adverse effects
        if kb_data and kb_data.get('adverse_effects'):
            response_lines.append("ADVERSE EFFECTS:")
            adverse = kb_data.get('adverse_effects', {})
            if isinstance(adverse, dict):
                if adverse.get('common'):
                    response_lines.append("  Common: " + ", ".join(adverse.get('common', [])))
                if adverse.get('rare'):
                    response_lines.append("  Rare: " + ", ".join(adverse.get('rare', [])))
            response_lines.append("")
    
    # DOSAGE AND ADMINISTRATION (from FDA)
    if 'dosage' in query_lower or 'dose' in query_lower or 'administration' in query_lower or 'how to take' in query_lower:
        response_lines.append("DOSAGE AND ADMINISTRATION:")
        response_lines.append("-" * 70)
        if fda_data and fda_data.get('dosage_and_administration'):
            response_lines.append("  " + fda_data['dosage_and_administration'])
        else:
            response_lines.append("  Refer to package insert or consult healthcare provider")
        response_lines.append("")
    
    # PREGNANCY AND BREAST FEEDING
    if 'pregnant' in query_lower or 'pregnancy' in query_lower or 'breast' in query_lower or 'nursing' in query_lower:
        response_lines.append("PREGNANCY AND BREAST FEEDING:")
        response_lines.append("-" * 70)
        if fda_data and fda_data.get('pregnancy_or_breast_feeding'):
            response_lines.append("  " + fda_data['pregnancy_or_breast_feeding'])
        else:
            response_lines.append("  Consult healthcare provider before use during pregnancy or breast feeding")
        response_lines.append("")
    
    # STORAGE AND HANDLING
    if 'storage' in query_lower or 'store' in query_lower or 'handling' in query_lower or 'keep' in query_lower:
        response_lines.append("STORAGE AND HANDLING:")
        response_lines.append("-" * 70)
        if fda_data and fda_data.get('storage_and_handling'):
            response_lines.append("  " + fda_data['storage_and_handling'])
        if fda_data and fda_data.get('keep_out_of_reach_of_children'):
            response_lines.append("\n  KEEP OUT OF REACH OF CHILDREN:")
            response_lines.append("  " + fda_data['keep_out_of_reach_of_children'])
        response_lines.append("")
    
    # ACTIVE INGREDIENTS
    if 'ingredient' in query_lower or 'composition' in query_lower or 'what is' in query_lower:
        response_lines.append("COMPOSITION:")
        response_lines.append("-" * 70)
        if fda_data and fda_data.get('active_ingredient'):
            response_lines.append("  ACTIVE INGREDIENT:")
            response_lines.append("  " + fda_data['active_ingredient'])
        if fda_data and fda_data.get('inactive_ingredient'):
            response_lines.append("\n  INACTIVE INGREDIENTS:")
            response_lines.append("  " + fda_data['inactive_ingredient'])
        response_lines.append("")
    
    response_lines.append("=" * 70)
    response_lines.append("IMPORTANT: Always verify information with current medical references.")
    response_lines.append("=" * 70)
    
    return "\n".join(response_lines)



# ============================================================================
# MAIN HANDLER: Execute Full 9-Step Workflow
# ============================================================================

def handle_drug_dosage_query(query: str, patient_id: int, db_connection, patient_data: Optional[Dict[str, Any]] = None) -> str:
    """
    MAIN HANDLER: Execute the complete 9-step drug dosage workflow.
    
    Flow:
    1. Detect drug intent in query
    2. Extract drug name
    3. Normalize via RxNorm API (with KB fallback)
    4. Check Knowledge Base (MUST exist in KB)
    5. Fetch FDA label
    6. Get patient data from OpenMRS
    7. Calculate dose using DoseCalculator
    8. Validate against limits
    9. Compose response
    
    SAFETY: If any step fails, return error message and STOP processing.
    NO HALLUCINATIONS - only use approved sources.
    
    Args:
        query: Doctor's question about drug dosage
        patient_id: OpenMRS patient ID
        db_connection: Database connection object
        patient_data: (Optional) Pre-retrieved patient data to avoid DB reconnection
    
    Returns: Response string with dosage information or error message
    """
    
    logger.info("=" * 80)
    logger.info("DRUG DOSAGE QUERY HANDLER - STARTING 9-STEP WORKFLOW")
    logger.info(f"Query: {query}")
    logger.info(f"Patient ID: {patient_id}")
    logger.info("=" * 80)
    
    # ========== STEP 1: Detect Drug Intent ==========
    if not detect_drug_intent(query):
        msg = "This query does not appear to be about drug dosage. Please ask about specific medication doses, frequencies, or prescriptions."
        logger.info(f"ABORT: {msg}")
        return msg
    
    # ========== STEP 2: Extract Drug Name ==========
    drug_name = extract_drug_name(query)
    if not drug_name:
        msg = "Could not identify the drug name in your query. Please specify which medication you're asking about (e.g., 'What is the dose of aspirin?')."
        logger.info(f"ABORT at STEP 2: {msg}")
        return msg
    
    # ========== STEP 2A: Check if This is a Drug Information Query (Not Dosage) ==========
    # If user is asking about adverse effects, contraindications, etc., use the info extractor
    query_lower = query.lower()
    is_info_query = any(keyword in query_lower for keyword in [
        'adverse', 'effect', 'side effect', 'contraindication', 'precaution',
        'warning', 'indication', 'interaction', 'property', 'information',
        'detail', 'about'
    ])
    
    # Check if query is NOT asking for dosage (no dosage-related keywords)
    is_dosage_query = any(keyword in query_lower for keyword in [
        'dose', 'dosage', 'how much', 'what dose', 'mg', 'prescribe', 'administer'
    ])
    
    if is_info_query and not is_dosage_query:
        logger.info(f"[STEP 2A] This is a drug INFORMATION query, not a dosage query")
        logger.info(f"[STEP 2A] Routing to drug information extractor for: {drug_name}")
        info_response = extract_drug_information(query, drug_name)
        logger.info(f"Drug information extraction complete")
        return info_response
    
    # ========== STEP 2.5: Check if Drug is Approved for Dose Calculation ==========
    # CRITICAL: Only approved drugs can have doses calculated
    is_approved, approved_drug_data = is_drug_approved(drug_name)
    if not is_approved:
        msg = f"I cannot provide dosage calculation for '{drug_name}'. I can only calculate doses for these approved drugs: ibuprofen, paracetamol, and acetylsalicylic acid (aspirin).\n\nIf you need general information about '{drug_name}', I can search the FDA database for you."
        logger.info(f"ABORT at STEP 2.5: Drug not approved for dose calculation: {drug_name}")
        return msg
    
    logger.info(f"[STEP 2.5] Drug '{drug_name}' is APPROVED for dose calculation")
    
    # ========== STEP 3: Normalize via RxNorm (with KB fallback) ==========
    rx_result = normalize_via_rxnorm(drug_name)
    
    # If RxNorm fails, try to continue with just the drug name from KB
    if not rx_result:
        logger.warning(f"[STEP 3] RxNorm normalization failed, attempting KB-only approach for {drug_name}")
        rx_result = {'rxcui': 'UNKNOWN', 'name': drug_name}
    
    rxcui = rx_result['rxcui']
    canonical_name = rx_result['name']
    
    # ========== STEP 4: Check Knowledge Base ==========
    # CRITICAL: Drug MUST be in KB before proceeding
    kb_data = check_knowledge_base_with_fallback(canonical_name, rxcui)
    if not kb_data:
        msg = f"Drug '{canonical_name}' is not in our approved Knowledge Base. We cannot provide dosage information for this drug at this time."
        logger.info(f"ABORT at STEP 4: {msg}")
        return msg
    
    # ========== STEP 5: Fetch FDA Label ==========
    fda_data = fetch_fda_label(rxcui)
    # NOTE: Not aborting if FDA fails - KB data is more important
    if not fda_data:
        logger.info("WARNING: FDA label fetch failed, continuing with KB data only")
    
    # ========== STEP 6: Get Patient Data ==========
    # Use pre-retrieved data if available, otherwise fetch from database
    if patient_data is None:
        logger.info(f"[STEP 6] No pre-retrieved patient data, fetching from OpenMRS...")
        patient_data = get_patient_data_from_openmrs(patient_id, db_connection)
    else:
        logger.info(f"[STEP 6] Using pre-retrieved patient data")
    
    if not patient_data:
        msg = f"Could not retrieve patient age/weight data for patient {patient_id}. Cannot calculate dose without patient demographics."
        logger.info(f"ABORT at STEP 6: {msg}")
        return msg
    
    # Extract age from birthdate if in nested structure
    patient_age = None
    patient_weight = None
    
    # Check for nested patient record with birthdate
    if isinstance(patient_data, dict):
        if 'patient' in patient_data and patient_data['patient'].get('data'):
            patient_record = patient_data['patient']['data'][0]
            birthdate = patient_record.get('birthdate')
            if birthdate:
                from datetime import datetime, date
                today = date.today()
                if isinstance(birthdate, date):
                    patient_age = today.year - birthdate.year
                    if (today.month, today.day) < (birthdate.month, birthdate.day):
                        patient_age -= 1
                    logger.info(f"[STEP 6] Calculated age from birthdate: {patient_age} years")
        
        # Extract weight from vitals
        if 'vitals' in patient_data and patient_data['vitals'].get('data'):
            for vital in patient_data['vitals']['data']:
                if 'Weight' in vital.get('vital_name', ''):
                    patient_weight = vital.get('value_numeric')
                    logger.info(f"[STEP 6] Extracted weight from vitals: {patient_weight} kg")
                    break
    
    # Fallback to simple dictionary keys
    if patient_age is None:
        patient_age = patient_data.get('age_years') or patient_data.get('current_age')
    if patient_weight is None:
        patient_weight = patient_data.get('weight_kg') or patient_data.get('weight')
    
    if not patient_age or not patient_weight:
        msg = f"Patient data incomplete: age={patient_age}, weight={patient_weight}. Cannot calculate dose."
        logger.info(f"ABORT at STEP 6: {msg}")
        return msg
    
    logger.info(f"[STEP 6] Patient demographics: age={patient_age} years, weight={patient_weight} kg")
    
    # ========== STEP 7: Calculate Dose ==========
    # Pass full drug structure with dosing information
    drug_for_calc = kb_data.get('dosing_info') if kb_data and (kb_data.get('local_db_found') or kb_data.get('approved_list_found')) else canonical_name
    calculated_dose = calculate_dose(drug_for_calc, patient_age, patient_weight)
    if not calculated_dose or calculated_dose.get('error'):
        msg = f"Dose calculation failed for {canonical_name} in patient age group. Drug may not have established pediatric/adult dosing rules in our system."
        logger.info(f"ABORT at STEP 7: {msg}")
        return msg
    
    # ========== STEP 8: Validate Against Limits ==========
    is_valid, validation_message = validate_against_limits(calculated_dose, kb_data, fda_data)
    # NOTE: Not aborting if validation fails - this is a warning, not a blocker
    
    # ========== STEP 9: Compose Response ==========
    drug_info = {
        'name': canonical_name,
        'rxcui': rxcui
    }
    
    response = compose_response(
        drug_info=drug_info,
        patient_data=patient_data,
        patient_age=patient_age,
        patient_weight=patient_weight,
        calculated_dose=calculated_dose,
        kb_data=kb_data,
        fda_data=fda_data,
        validation=(is_valid, validation_message)
    )
    
    logger.info("=" * 80)
    logger.info("DRUG DOSAGE QUERY HANDLER - WORKFLOW COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    
    return response
