"""
Medication MCP Controller
Main controller combining KnowledgeLoader and DoseCalculator
"""

from utils.knowledge_loader import KnowledgeLoader
from utils.dose_calculator import DoseCalculator


class MedicationMCPController:
    """
    Medication controller - Main API for medication processing
    Combines: knowledge base lookup + pediatric dose calculation
    """

    def __init__(self):
        """Initialize medication controller with knowledge loader and dose calculator"""
        self.knowledge_loader = KnowledgeLoader()
        self.dose_calc = DoseCalculator()

    def process(self, drug_name, weight_kg=None, age_years=None):
        """
        Process medication query with dose calculation
        
        Args:
            drug_name: Name of medication
            weight_kg: Patient weight in kg (optional)
            age_years: Patient age in years (optional)
        
        Returns:
            Dictionary with drug info and calculated dose (if patient data provided)
        """
        # Get drug JSON from knowledge base
        drug = self.knowledge_loader.find_drug(drug_name)

        if not drug:
            return {"error": "Drug not found in knowledge base"}

        # If patient data provided, calculate dose
        if weight_kg is not None and age_years is not None:
            dose = self.dose_calc.calculate_dose(
                weight_kg=weight_kg,
                age_years=age_years,
                drug=drug
            )
        else:
            dose = None

        result = {
            "drug": drug_name,
            "drug_info": drug,
            "source": "Local pediatric dosing knowledge base"
        }
        
        if dose:
            result["calculated_dose"] = dose

        return result
