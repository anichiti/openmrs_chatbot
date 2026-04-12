"""
FDA API Skill - Drug label information retrieval
Fetches drug information from FDA Open Data API
"""

import requests
import re
import logging

logger = logging.getLogger(__name__)

class FDAAPISkill:
    """Fetch drug labels and information from FDA API"""

    BASE_URL = "https://api.fda.gov/drug/label.json"

    # ---------------------------------------------
    # CLEAN FDA TEXT
    # ---------------------------------------------
    def clean_fda_text(self, text_list, max_length=600):
        """
        Clean and format FDA response text
        
        Args:
            text_list: List of text strings
            max_length: Maximum length of output (default 600 chars)
        
        Returns:
            Cleaned text string or None
        """
        if not text_list:
            return None

        text = " ".join(text_list)

        # Remove leading numbers and all-caps headers
        text = re.sub(
            r'^\d+\s+[A-Z\s]+(?=[A-Z][a-z])',
            '',
            text
        )

        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove problematic Unicode characters that cause encoding issues
        # Replace em-dashes, en-dashes, hyphens with ASCII equivalent
        text = text.replace('\u2014', '-')  # em dash
        text = text.replace('\u2013', '-')  # en dash
        text = text.replace('\u2011', '-')  # non-breaking hyphen
        text = text.replace('\u00ad', '')   # soft hyphen
        
        # Remove other special Unicode characters that might cause terminal issues
        text = text.encode('ascii', 'ignore').decode('ascii')

        text = text.strip()

        # Limit length
        if len(text) > max_length:
            return text[:max_length] + "..."

        return text

    # ---------------------------------------------
    # GET FDA LABEL DATA
    # ---------------------------------------------
    def get_drug_label(self, generic_name):
        """
        Fetch FDA drug label information
        
        Args:
            generic_name: Generic name of drug
        
        Returns:
            Dictionary with label data: indications, warnings, contraindications, adverse_reactions,
            dosage_and_administration, do_not_use, ask_doctor, pregnancy, storage, etc.
        """
        query = f"?search=openfda.generic_name:{generic_name}&limit=1"
        url = self.BASE_URL + query
        
        try:
            response = requests.get(url, timeout=5)

            if response.status_code != 200:
                return {"warning": "No FDA label data found"}

            data = response.json()
            results = data.get("results", [])

            if not results:
                return {"warning": "No FDA results"}

            label = results[0]

            return {
                "drug_name": generic_name,
                
                # Core clinical information
                "indications": self.clean_fda_text(
                    label.get("indications_and_usage")
                ),
                "dosage_and_administration": self.clean_fda_text(
                    label.get("dosage_and_administration")
                ),
                "warnings": self.clean_fda_text(
                    label.get("warnings")
                ),
                "contraindications": self.clean_fda_text(
                    label.get("contraindications")
                ),
                "adverse_reactions": self.clean_fda_text(
                    label.get("adverse_reactions")
                ),
                
                # Additional safety information
                "do_not_use": self.clean_fda_text(
                    label.get("do_not_use")
                ),
                "ask_doctor": self.clean_fda_text(
                    label.get("ask_doctor")
                ),
                "ask_doctor_or_pharmacist": self.clean_fda_text(
                    label.get("ask_doctor_or_pharmacist")
                ),
                "stop_use": self.clean_fda_text(
                    label.get("stop_use")
                ),
                
                # Special populations
                "pregnancy_or_breast_feeding": self.clean_fda_text(
                    label.get("pregnancy_or_breast_feeding")
                ),
                
                # Storage and handling
                "storage_and_handling": self.clean_fda_text(
                    label.get("storage_and_handling")
                ),
                "keep_out_of_reach_of_children": self.clean_fda_text(
                    label.get("keep_out_of_reach_of_children")
                ),
                
                # Drug composition
                "active_ingredient": self.clean_fda_text(
                    label.get("active_ingredient"), max_length=1000
                ),
                "inactive_ingredient": self.clean_fda_text(
                    label.get("inactive_ingredient"), max_length=1000
                ),
                "purpose": self.clean_fda_text(
                    label.get("purpose")
                ),
                
                # Metadata
                "effective_time": label.get("effective_time"),
            }
            
        except (requests.Timeout, requests.RequestException) as e:
            logger.warning(f"FDA API timeout or request error for '{generic_name}': {e}. Using local knowledge base.")
            return {"warning": "FDA API timeout - using local knowledge base"}
        except Exception as e:
            logger.error(f"Unexpected error fetching FDA label for '{generic_name}': {e}")
            return {"error": str(e)}
