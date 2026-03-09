"""
RxNorm API Skill - Drug name normalization
Converts brand names to generic names using RxNav API
"""

import requests


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
        try:
            url = f"{self.BASE_URL}/rxcui.json?name={drug_name}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            rxcui_list = data.get("idGroup", {}).get("rxnormId", [])

            if not rxcui_list:
                return None

            return rxcui_list[0]

        except Exception as e:
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

        try:
            # Get active ingredient name
            url = f"{self.BASE_URL}/rxcui/{rxcui}/related.json?tty=IN"

            response = requests.get(url, timeout=10)
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

        except Exception as e:
            return {"error": str(e)}
