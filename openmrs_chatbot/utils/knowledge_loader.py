"""
Knowledge Loader - Load and search medication knowledge base
Searches drug names, generic names, and aliases
"""

import json
import os


class KnowledgeLoader:
    """Load medication data from JSON knowledge base"""

    def __init__(self, file_name="medical_drugs.json"):
        """
        Initialize knowledge loader
        
        Args:
            file_name: Name of JSON file in data/ folder (default: medical_drugs.json)
        """
        # Get path to data folder
        base_path = os.path.dirname(os.path.dirname(__file__))
        self.file_path = os.path.join(base_path, "data", file_name)

    def load_knowledge(self):
        """Load knowledge base from JSON file"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Knowledge base not found: {self.file_path}")
        
        with open(self.file_path, "r") as f:
            return json.load(f)

    def find_drug(self, drug_name):
        """
        Find drug in knowledge base by name, generic name, or alias
        
        Args:
            drug_name: Name to search (can be brand name or generic)
        
        Returns:
            Drug dictionary or None if not found
        """
        try:
            data = self.load_knowledge()
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return None
        
        drug_name = drug_name.lower()

        for drug in data.get("drugs", []):

            # Check generic_name
            generic = drug.get("generic_name", "").lower()
            if drug_name == generic:
                return drug

            # Check drug_name
            drug_field = drug.get("drug_name", "").lower()
            if drug_name == drug_field:
                return drug

            # Check aliases
            aliases = [a.lower() for a in drug.get("aliases", [])]
            if drug_name in aliases:
                return drug

        return None
