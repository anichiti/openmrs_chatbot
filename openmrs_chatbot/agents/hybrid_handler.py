"""
Hybrid Question Handler - Processes questions requiring both allergy and medication handling.
Combines safety checks, dosage information, and drug contraindications.
"""

import json
from utils.logger import setup_logger
from agents.medication_openmrs_fetcher import MedicationOpenMRSFetcher
from agents.allergy_openmrs_fetcher import AllergyOpenMRSFetcher
from agents.medication_response import MedicationResponseDoctor, MedicationResponsePatient
from agents.allergy_response import AllergyResponseDoctor, AllergyResponsePatient

logger = setup_logger(__name__)


class HybridQuestionHandler:
    """Processes questions that need both allergy and medication information"""
    
    def __init__(self):
        logger.info("Initializing HybridQuestionHandler")
        self.med_fetcher = MedicationOpenMRSFetcher()
        self.allergy_fetcher = AllergyOpenMRSFetcher()
    
    def handle_hybrid_query(self, question, patient_id, user_type, intent_breakdown):
        """
        Process hybrid question by checking both medication and allergy information.
        
        Args:
            question (str): The user's question
            patient_id (str): Patient ID to check records for
            user_type (str): 'doctor' or 'patient'
            intent_breakdown (dict): Breakdown of what the question needs
        
        Returns:
            dict: Combined response with medication and allergy information
        """
        logger.info(f"[HYBRID HANDLER] Starting for patient {patient_id}")
        
        results = {
            "status": "success",
            "response": "",
            "medication_info": None,
            "allergy_info": None,
            "safety_warning": None,
            "combined_assessment": None,
            "sources": [],
            "patient_id": patient_id
        }
        
        try:
            # Step 1: Get medication information if requested
            if intent_breakdown.get("needs_dosage"):
                logger.info(f"[HYBRID] Fetching medication information")
                results["medication_info"] = self.med_fetcher.fetch_medication_info(
                    question, patient_id
                )
                results["sources"].append("medication_database")
            
            # Step 2: Get allergy information if requested
            if intent_breakdown.get("needs_safety_check"):
                logger.info(f"[HYBRID] Fetching allergy information")
                
                # If specific drug mentioned, check for contraindication
                drug_name = intent_breakdown.get("mentioned_drug")
                if drug_name:
                    results["allergy_info"] = self.allergy_fetcher.check_drug_allergy(
                        patient_id, drug_name
                    )
                else:
                    # Get general allergies
                    results["allergy_info"] = self.allergy_fetcher.fetch_patient_allergies(
                        patient_id
                    )
                
                results["sources"].append("allergy_database")
            
            # Step 3: Combine information into safety assessment
            results["combined_assessment"] = self._create_safety_assessment(
                results.get("medication_info"),
                results.get("allergy_info"),
                intent_breakdown.get("mentioned_drug")
            )
            
            # Step 4: Format response based on user type
            results["response"] = self._format_hybrid_response(
                results["combined_assessment"],
                results.get("medication_info"),
                results.get("allergy_info"),
                user_type
            )
            
            logger.info(f"[HYBRID] Successfully processed hybrid question")
            
        except Exception as e:
            logger.error(f"[HYBRID] Error processing hybrid query: {str(e)}")
            results["status"] = "error"
            results["response"] = f"Error processing your question: {str(e)}"
        
        return results
    
    def _create_safety_assessment(self, medication_info, allergy_info, drug_name):
        """Create a combined safety assessment from medication and allergy data"""
        assessment = {
            "is_safe": True,
            "warnings": [],
            "recommendations": [],
            "drug_name": drug_name
        }
        
        try:
            # Check for contraindications
            if allergy_info and isinstance(allergy_info, dict):
                if allergy_info.get("has_allergy"):
                    assessment["is_safe"] = False
                    allergen = allergy_info.get("allergen")
                    severity = allergy_info.get("severity", "unknown")
                    assessment["warnings"].append(
                        f"ALLERGY ALERT: Patient has documented allergy to {allergen} (Severity: {severity})"
                    )
                
                if allergy_info.get("contraindications"):
                    for contraindication in allergy_info["contraindications"]:
                        assessment["is_safe"] = False
                        assessment["warnings"].append(
                            f"CONTRAINDICATION: {contraindication}"
                        )
            
            # Add medication information
            if medication_info and isinstance(medication_info, dict):
                if dosage := medication_info.get("recommended_dosage"):
                    assessment["recommendations"].append(
                        f"Recommended dosage: {dosage}"
                    )
                
                if side_effects := medication_info.get("side_effects"):
                    assessment["warnings"].extend(
                        [f"Possible side effect: {se}" for se in side_effects[:3]]
                    )
            
        except Exception as e:
            logger.error(f"Error creating safety assessment: {e}")
            assessment["assessment_error"] = str(e)
        
        return assessment
    
    def _format_hybrid_response(self, assessment, medication_info, allergy_info, user_type):
        """Format the combined response for the user"""
        response_parts = []
        
        try:
            # Safety status
            if assessment["is_safe"]:
                safety_message = "✓ No contraindications found. This medication appears safe."
            else:
                safety_message = "⚠ IMPORTANT SAFETY CONCERN: There are contraindications or allergies that must be considered."
            
            response_parts.append(safety_message)
            
            # Warnings
            if assessment["warnings"]:
                response_parts.append("\n[WARNINGS]")
                for warning in assessment["warnings"]:
                    response_parts.append(f"  • {warning}")
            
            # Recommendations
            if assessment["recommendations"]:
                response_parts.append("\n[RECOMMENDATIONS]")
                for rec in assessment["recommendations"]:
                    response_parts.append(f"  • {rec}")
            
            # Additional medication details for doctors
            if user_type.lower() == "doctor" and medication_info:
                response_parts.append("\n[MEDICATION DETAILS]")
                if interactions := medication_info.get("drug_interactions"):
                    response_parts.append(f"  Drug Interactions: {', '.join(interactions[:3])}")
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            response_parts.append(f"Note: Some details could not be formatted: {str(e)}")
        
        return "\n".join(response_parts)
