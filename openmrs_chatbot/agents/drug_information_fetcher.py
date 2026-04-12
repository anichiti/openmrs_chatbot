"""
Drug Information Fetcher with FDA API and RxNorm Integration
Retrieves comprehensive drug information including side effects, contraindications, warnings, etc.
"""

import requests
from utils.logger import setup_logger
import os
import time

logger = setup_logger(__name__)

# FDA API Configuration
FDA_API_BASE = "https://api.fda.gov/drug"
RXNORM_API_BASE = "https://rxnav.nlm.nih.gov/REST"

# Optional FDA API Key (from environment variable)
FDA_API_KEY = os.getenv("FDA_API_KEY", None)

# Rate limiting
REQUEST_TIMEOUT = 5
RETRY_DELAY = 0.5


class DrugInformationFetcher:
    """Fetch comprehensive drug information from FDA and RxNorm APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = REQUEST_TIMEOUT
    
    def _normalize_drug_name(self, drug_name):
        """
        Normalize drug name using RxNorm API
        Tries multiple search approaches to find the drug.
        
        Args:
            drug_name: Drug name to normalize
        
        Returns:
            Dict with normalized name and RxCUI (RxNorm Concept Unique ID)
        """
        try:
            url = f"{RXNORM_API_BASE}/rxcui.json"
            
            # Try multiple search strategies
            search_attempts = [
                # Exact search
                {"name": drug_name, "search": "1"},
                # Approximate search
                {"name": drug_name, "search": "2"},
            ]
            
            for attempt in search_attempts:
                try:
                    params = attempt
                    response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("idGroup", {}).get("rxuiConceptList"):
                        # Get the first concept as the primary match
                        concept = data["idGroup"]["rxuiConceptList"][0]
                        rxcui = concept.get("rxcui")
                        name = concept.get("name", drug_name)
                        
                        logger.info(f"[DRUG] Normalized '{drug_name}' to '{name}' (RxCUI: {rxcui})")
                        return {
                            "normalized_name": name,
                            "rxcui": rxcui,
                            "status": "found"
                        }
                
                except Exception as attempt_error:
                    logger.debug(f"[DRUG] RxNorm search attempt {attempt} failed: {attempt_error}")
                    continue
            
            logger.warning(f"[DRUG] Could not normalize '{drug_name}' via RxNorm - will proceed with original name")
            return {
                "normalized_name": drug_name,
                "rxcui": None,
                "status": "not_found"
            }
        
        except requests.exceptions.Timeout:
            logger.warning(f"[DRUG] RxNorm API timeout for '{drug_name}'")
            return {"normalized_name": drug_name, "rxcui": None, "status": "timeout"}
        except Exception as e:
            logger.error(f"[DRUG] Error normalizing drug name '{drug_name}': {e}")
            return {"normalized_name": drug_name, "rxcui": None, "status": "error"}
    
    def _get_fda_drug_label(self, drug_name):
        """
        Fetch drug label information from FDA OpenFDA API
        Tries multiple query strategies to find the drug data.
        
        Args:
            drug_name: Drug name
        
        Returns:
            Dict with side effects, contraindications, warnings, etc.
        """
        try:
            url = f"{FDA_API_BASE}/label.json"
            
            # Multiple search strategies (in order of preference)
            search_queries = [
                # Strategy 1: Search by openfda generic_name field
                f'openfda.generic_name:"{drug_name}"',
                # Strategy 2: Search by openfda brand_name field
                f'openfda.brand_name:"{drug_name}"',
                # Strategy 3: Search by substance (active ingredient)
                f'substance_name:"{drug_name}"',
                # Strategy 4: Fuzzy brand name search
                f'brand_name:"{drug_name.lower()}"',
                # Strategy 5: Any text containing drug name (broader search)
                drug_name
            ]
            
            # Try each search strategy
            data = None
            for search_query in search_queries:
                try:
                    params = {
                        "search": search_query,
                        "limit": "1"
                    }
                    
                    # Add API key if available
                    if FDA_API_KEY:
                        params["api_key"] = FDA_API_KEY
                    
                    logger.debug(f"[DRUG] Trying FDA search with query: {search_query}")
                    
                    response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        logger.info(f"[DRUG] FDA search succeeded with strategy: {search_query}")
                        break
                    
                except requests.exceptions.HTTPError as he:
                    if he.response.status_code == 404:
                        logger.debug(f"[DRUG] FDA search returned 404 for query: {search_query}")
                        continue
                    else:
                        raise
            
            # If we got data, extract information
            if data and data.get("results") and len(data["results"]) > 0:
                result = data["results"][0]
                
                # Extract from openfda section if available
                openfda = result.get("openfda", {})
                
                # Debug: Log all available fields in the FDA response
                logger.info(f"[DRUG] FDA API response fields available: {list(result.keys())}")
                
                # Extract all available information from FDA label
                # The FDA API returns these fields as arrays, so we take the first element
                drug_info = {
                    "brand_name": (openfda.get("brand_name") or ["Unknown"])[0] if openfda.get("brand_name") else "Unknown",
                    "generic_name": (openfda.get("generic_name") or ["Unknown"])[0] if openfda.get("generic_name") else "Unknown",
                    "manufacturer": (openfda.get("manufacturer_name") or ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
                    
                    # Active ingredients
                    "active_ingredients": result.get("active_ingredient", ["Not available"])[0] if result.get("active_ingredient") else "Not available",
                    
                    # Purpose / What it does
                    "purpose": result.get("purpose", ["Not available"])[0] if result.get("purpose") else "Not available",
                    
                    # Indications and usage - WHAT IS IT USED FOR
                    "indications": result.get("indications_and_usage", ["Not available"])[0] if result.get("indications_and_usage") else "Not available",
                    
                    # Side effects / Adverse reactions
                    "side_effects": result.get("adverse_reactions", ["Not available"])[0] if result.get("adverse_reactions") else "Not available",
                    
                    # Do not use (contraindications)
                    "do_not_use": result.get("do_not_use", ["Not available"])[0] if result.get("do_not_use") else "Not available",
                    
                    # Contraindications (alternative field)
                    "contraindications": result.get("contraindications", ["Not available"])[0] if result.get("contraindications") else "Not available",
                    
                    # When to ask doctor (precautions)
                    "ask_doctor": result.get("ask_doctor", ["Not available"])[0] if result.get("ask_doctor") else "Not available",
                    "ask_doctor_or_pharmacist": result.get("ask_doctor_or_pharmacist", ["Not available"])[0] if result.get("ask_doctor_or_pharmacist") else "Not available",
                    
                    # Warnings (try multiple field names)
                    "warnings": (result.get("warnings", None) or result.get("warnings_and_cautions", ["Not available"]))[0] if (result.get("warnings") or result.get("warnings_and_cautions")) else "Not available",
                    
                    # Black box warning (serious/critical warning)
                    "boxed_warning": result.get("boxed_warning", ["Not available"])[0] if result.get("boxed_warning") else "Not available",
                    
                    # When to stop use
                    "stop_use": result.get("stop_use", ["Not available"])[0] if result.get("stop_use") else "Not available",
                    
                    # Precautions and other warnings
                    "precautions": result.get("precautions", ["Not available"])[0] if result.get("precautions") else "Not available",
                    
                    # Drug interactions
                    "drug_interactions": result.get("drug_interactions", ["Not available"])[0] if result.get("drug_interactions") else "Not available",
                    
                    # Pregnancy and breastfeeding
                    "pregnancy": result.get("pregnancy_or_breast_feeding", ["Not available"])[0] if result.get("pregnancy_or_breast_feeding") else (result.get("pregnancy_or_lactation", ["Not available"])[0] if result.get("pregnancy_or_lactation") else "Not available"),
                    
                    # Nursing mothers (alternative field)
                    "nursing": result.get("nursing_mothers", ["Not available"])[0] if result.get("nursing_mothers") else "Not available",
                    
                    # Additional useful fields
                    "dosage": result.get("dosage_and_administration", ["Not available"])[0] if result.get("dosage_and_administration") else "Not available",
                    "description": result.get("description", ["Not available"])[0] if result.get("description") else "Not available",
                    "storage": result.get("storage_and_handling", ["Not available"])[0] if result.get("storage_and_handling") else "Not available",
                    "keep_out_of_reach": result.get("keep_out_of_reach_of_children", ["Not available"])[0] if result.get("keep_out_of_reach_of_children") else "Not available",
                    "inactive_ingredients": result.get("inactive_ingredient", ["Not available"])[0] if result.get("inactive_ingredient") else "Not available",
                }
                
                # Log which fields actually have data
                populated_fields = [k for k, v in drug_info.items() if v != "Not available"]
                logger.info(f"[DRUG] Fields with data for '{drug_name}': {populated_fields}")
                logger.debug(f"[DRUG] Complete drug info extracted: {drug_info}")
                
                logger.info(f"[DRUG] Found FDA label data for '{drug_name}'")
                return {
                    "status": "found",
                    "data": drug_info
                }
            else:
                logger.warning(f"[DRUG] No FDA label found for '{drug_name}' after trying all search strategies")
                return {
                    "status": "not_found",
                    "data": None
                }
        
        except requests.exceptions.Timeout:
            logger.warning(f"[DRUG] FDA API timeout for '{drug_name}'")
            return {"status": "timeout", "data": None}
        except Exception as e:
            logger.error(f"[DRUG] Error fetching FDA label for '{drug_name}': {e}")
            return {"status": "error", "data": None}
    
    def _get_rxnorm_properties(self, rxcui):
        """
        Fetch drug properties from RxNorm including interactions
        
        Args:
            rxcui: RxNorm Concept Unique ID
        
        Returns:
            Dict with drug properties and interactions
        """
        if not rxcui:
            return {"status": "no_rxcui", "data": None}
        
        try:
            # Get drug properties
            url = f"{RXNORM_API_BASE}/rxcui/{rxcui}/properties.json"
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            properties = {
                "rxcui": rxcui,
                "name": data.get("properties", {}).get("name", "Unknown"),
                "tty": data.get("properties", {}).get("tty", "Unknown"),
                "status": "found"
            }
            
            logger.info(f"[DRUG] Found RxNorm properties for RxCUI {rxcui}")
            return {"status": "found", "data": properties}
        
        except requests.exceptions.Timeout:
            logger.warning(f"[DRUG] RxNorm properties API timeout for RxCUI {rxcui}")
            return {"status": "timeout", "data": None}
        except Exception as e:
            logger.error(f"[DRUG] Error fetching RxNorm properties for RxCUI {rxcui}: {e}")
            return {"status": "error", "data": None}
    
    def get_comprehensive_drug_info(self, drug_name):
        """
        Get comprehensive drug information from multiple sources
        
        Args:
            drug_name: Drug name to look up
        
        Returns:
            Dict with complete drug information
        """
        try:
            logger.info(f"[DRUG] Fetching comprehensive information for '{drug_name}'")
            
            # Step 1: Normalize drug name
            normalized = self._normalize_drug_name(drug_name)
            
            # Step 2: Fetch FDA label data
            time.sleep(RETRY_DELAY)  # Rate limiting
            fda_data = self._get_fda_drug_label(normalized["normalized_name"])
            
            # Step 3: Fetch RxNorm properties if available
            time.sleep(RETRY_DELAY)  # Rate limiting
            rxnorm_data = self._get_rxnorm_properties(normalized.get("rxcui"))
            
            result = {
                "search_term": drug_name,
                "normalized_name": normalized["normalized_name"],
                "rxcui": normalized.get("rxcui"),
                "fda_label_status": fda_data["status"],
                "rxnorm_status": rxnorm_data["status"],
                "fda_data": fda_data.get("data"),
                "rxnorm_data": rxnorm_data.get("data")
            }
            
            logger.info(f"[DRUG] Comprehensive data retrieved for '{drug_name}'")
            return result
        
        except Exception as e:
            logger.error(f"[DRUG] Error fetching comprehensive drug info for '{drug_name}': {e}")
            return {
                "search_term": drug_name,
                "error": str(e),
                "status": "error"
            }
    
    def search_drug_interactions(self, drug_list):
        """
        Search for potential drug interactions
        
        Args:
            drug_list: List of drug names
        
        Returns:
            List of potential interactions
        """
        try:
            if len(drug_list) < 2:
                return {"status": "insufficient_drugs", "interactions": []}
            
            # Convert drug names to RxCUIs
            rxcuis = []
            for drug in drug_list:
                normalized = self._normalize_drug_name(drug)
                if normalized.get("rxcui"):
                    rxcuis.append(normalized["rxcui"])
            
            if len(rxcuis) < 2:
                return {"status": "could_not_normalize", "interactions": []}
            
            # Check for interactions using RxNorm
            url = f"{RXNORM_API_BASE}/interaction/list.json"
            params = {
                "rxcuis": "+".join(rxcuis)
            }
            
            time.sleep(RETRY_DELAY)  # Rate limiting
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            interactions = data.get("interactions", [])
            logger.info(f"[DRUG] Found {len(interactions)} potential interactions")
            
            return {
                "status": "found" if interactions else "no_interactions",
                "drug_ids": rxcuis,
                "interactions": interactions
            }
        
        except requests.exceptions.Timeout:
            logger.warning(f"[DRUG] Drug interactions API timeout")
            return {"status": "timeout", "interactions": []}
        except Exception as e:
            logger.error(f"[DRUG] Error fetching drug interactions: {e}")
            return {"status": "error", "interactions": [], "error": str(e)}


# Global instance
_drug_fetcher = None


def get_drug_fetcher():
    """Get or create global drug information fetcher instance"""
    global _drug_fetcher
    if _drug_fetcher is None:
        _drug_fetcher = DrugInformationFetcher()
    return _drug_fetcher
