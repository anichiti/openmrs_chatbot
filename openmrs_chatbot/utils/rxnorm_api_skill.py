"""
RxNorm API Skill - Drug name normalization
Converts brand names to generic names using RxNav API
"""

import requests
import logging

logger = logging.getLogger(__name__)

class RxNormAPISkill:
    """Normalize drug names using RxNav RESTful API"""

    BASE_URL = "https://rxnav.nlm.nih.gov/REST"

    # ---------------------------------------------
    # GET RXCUI FROM DRUG NAME
    # ---------------------------------------------
    def get_rxcui(self, drug_name):
        """
        Get RxCUI (unique identifier) for a drug name
        
        Args:
            drug_name: Name of medication (brand or generic)
        
        Returns:
            RxCUI string or None if not found
        """
        url = f"{self.BASE_URL}/rxcui.json?name={drug_name}"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()

            rxcui_list = data.get("idGroup", {}).get("rxnormId", [])

            if not rxcui_list:
                return None

            return rxcui_list[0]
            
        except (requests.Timeout, requests.RequestException) as e:
            logger.warning(f"RxNorm API timeout or request error for '{drug_name}': {e}. Using fallback.")
            return {"error": "RxNorm API timeout - using local data"}
        except Exception as e:
            logger.error(f"Unexpected error in get_rxcui for '{drug_name}': {e}")
            return {"error": str(e)}

    # ---------------------------------------------
    # NORMALIZE DRUG → GET GENERIC INGREDIENT
    # ---------------------------------------------
    def normalize_drug(self, drug_name):
        """
        Normalize drug name to generic ingredient
        Example: "Tylenol" → "paracetamol"
        
        Args:
            drug_name: Brand name or generic name
        
        Returns:
            Dictionary with rxcui and generic_name or error
        """
        rxcui = self.get_rxcui(drug_name)

        if not rxcui or isinstance(rxcui, dict):
            return {"error": "RxCUI not found"}

        url = f"{self.BASE_URL}/rxcui/{rxcui}/related.json?tty=IN"
        
        try:
            # Get active ingredient name
            response = requests.get(url, timeout=5)
            data = response.json()

            concepts = data.get("relatedGroup", {}).get("conceptGroup", [])

            for group in concepts:
                if group.get("tty") == "IN":
                    concept = group.get("conceptProperties", [])[0]
                    return {
                        "rxcui": rxcui,
                        "generic_name": concept.get("name")
                    }

            # fallback if ingredient not found
            return {
                "rxcui": rxcui,
                "generic_name": drug_name
            }
            
        except (requests.Timeout, requests.RequestException) as e:
            logger.warning(f"RxNorm API timeout or request error during normalize_drug for '{drug_name}': {e}. Using fallback.")
            return {"error": "RxNorm API timeout - using local data"}
        except Exception as e:
            logger.error(f"Unexpected error in normalize_drug for '{drug_name}': {e}")
            return {"error": str(e)}
