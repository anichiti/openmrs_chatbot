import json
import os
from utils.logger import setup_logger
from utils.config import MEDICATION_DB, IMMUNIZATION_DB, MILESTONE_DB

logger = setup_logger(__name__)

# Import extracted medication components (formerly from ani)
try:
    from agents.medication_controller import MedicationMCPController
    from utils.rxnorm_api_skill import RxNormAPISkill
    from utils.fda_api_skill import FDAAPISkill
    ANI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Medication components not available: {e}, using local JSON only")
    ANI_AVAILABLE = False


class MCPAgent:
    def __init__(self):
        self.medication_db = self._load_json(MEDICATION_DB)
        self.immunization_db = self._load_json(IMMUNIZATION_DB)
        self.milestone_db = self._load_json(MILESTONE_DB)
        
        # Initialize medication components for enhanced medication queries
        if ANI_AVAILABLE:
            try:
                self.ani_mcp = MedicationMCPController()
                self.ani_rxnorm = RxNormAPISkill()
                self.ani_fda = FDAAPISkill()
                logger.info("Medication components initialized (RxNorm + DoseCalc + FDA API)")
            except Exception as e:
                logger.warning(f" Medication component initialization failed: {e}, using local JSON only")
                self.ani_mcp = None
        else:
            self.ani_mcp = None

    def _load_json(self, filepath):
        if not os.path.exists(filepath):
            logger.error(f"Database not found: {filepath}")
            return {}
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Error loading {os.path.basename(filepath)}: {str(e)}")
            return {}

    def query_medication_db(self, drug_name=None, indication=None):
        results = []
        if not self.medication_db:
            return {"results": results, "count": 0}

        medications = self.medication_db.get("medications", [])

        for med in medications:
            match = True
            if drug_name:
                if drug_name.lower() not in med.get("name", "").lower():
                    match = False
            if indication:
                indications = med.get("indications", [])
                if not any(indication.lower() in ind.lower() for ind in indications):
                    match = False
            if match:
                results.append(med)

        return {"results": results, "count": len(results)}

    def query_immunization_db(self, vaccine_name=None, age_group=None):
        results = []
        if not self.immunization_db:
            return {"results": results, "count": 0}

        vaccines = self.immunization_db.get("vaccines", [])

        for vaccine in vaccines:
            match = True
            if vaccine_name:
                if vaccine_name.lower() not in vaccine.get("name", "").lower():
                    match = False
            if age_group:
                age_groups = vaccine.get("recommended_age_groups", [])
                if not any(age_group.lower() in ag.lower() for ag in age_groups):
                    match = False
            if match:
                results.append(vaccine)

        return {"results": results, "count": len(results)}

    def query_milestone_db(self, age_months=None, milestone_type=None):
        results = []
        if not self.milestone_db:
            return {"results": results, "count": 0}

        milestones = self.milestone_db.get("milestones", [])
        
        # SAFETY CHECK: Milestone data is for infants/toddlers (typically 3-60 months)
        # Do not return infant milestones for children > 60 months (5 years)
        max_milestone_age = max([m.get("age_months", 0) for m in milestones]) if milestones else 0
        if age_months and age_months > max_milestone_age:
            # Age is beyond available milestone data - return empty results
            # (this allows the handler to provide appropriate age-specific guidance)
            logger.info(f"Patient age {age_months} months exceeds available milestone data (max: {max_milestone_age} months)")
            return {"results": [], "count": 0, "note": f"Milestone data available only for ages 3-{max_milestone_age} months"}

        for milestone in milestones:
            match = True
            if age_months:
                milestone_age = milestone.get("age_months")
                # Exact match first
                if milestone_age == age_months:
                    match = True
                else:
                    # If no exact match and age is older, find closest milestone age
                    if age_months > milestone_age:
                        # For older ages, we can use the oldest available milestone as reference
                        match = False
                    else:
                        match = False
            if milestone_type:
                if milestone_type.lower() not in milestone.get("type", "").lower():
                    match = False
            if match:
                results.append(milestone)

        # If no exact match and age_months is specified, return closest match
        if not results and age_months:
            closest_milestone = None
            closest_diff = float('inf')
            for milestone in milestones:
                if milestone_type and milestone_type.lower() not in milestone.get("type", "").lower():
                    continue
                diff = abs(milestone.get("age_months", 0) - age_months)
                if diff < closest_diff:
                    closest_diff = diff
                    closest_milestone = milestone
            if closest_milestone:
                results.append(closest_milestone)

        return {"results": results, "count": len(results)}

    def search_medication(self, query_text):
        """
        Enhanced medication search using extracted components:
        - RxNorm API: Normalize drug names (brand → generic)
        - Dose Calculator: Calculate pediatric doses
        - FDA API: Get drug data from FDA
        
        Falls back to local JSON if components not available
        """
        results = []
        
        # Try medication components first (RxNorm + Dose Calc + FDA API)
        if self.ani_mcp:
            try:
                # Normalize drug name using RxNorm
                normalized = self._normalize_drug_name(query_text)
                if normalized:
                    # Try to get comprehensive drug data (dose + FDA)
                    medication_result = self._query_medication(normalized)
                    if medication_result:
                        logger.info(f" Used medication components for: {normalized}")
                        return medication_result
            except Exception as e:
                logger.warning(f" Medication query failed: {e}, falling back to local JSON")
        
        # Fallback: search local JSON database
        if not self.medication_db:
            return {"results": results, "count": 0}

        medications = self.medication_db.get("medications", [])

        for med in medications:
            if (query_text.lower() in med.get("name", "").lower() or
                query_text.lower() in med.get("description", "").lower() or
                any(query_text.lower() in ind.lower() for ind in med.get("indications", []))):
                results.append(med)

        logger.info(f"Used local JSON: {len(results)} results")
        return {"results": results, "count": len(results)}

    def _normalize_drug_name(self, drug_name):
        """
        Normalize drug name using RxNorm API
        Converts brand names to generic names
        Example: "Tylenol" → "paracetamol"
        """
        try:
            if not self.ani_rxnorm:
                return None
            
            result = self.ani_rxnorm.normalize_drug(drug_name)
            if isinstance(result, dict) and "generic_name" in result:
                generic = result["generic_name"]
                logger.info(f"RxNorm: '{drug_name}' -> '{generic}'")
                return generic
        except Exception as e:
            logger.debug(f"RxNorm normalization failed: {e}")
        
        return None
    
    def _query_medication(self, normalized_drug_name):
        """
        Query medication system for:
        - Drug info (indications, contraindications)
        - Dose calculations (if used with patient data)
        - FDA drug label data
        """
        try:
            if not self.ani_mcp:
                return None
            
            # Get drug from medication knowledge base
            drug_data = self.ani_mcp.knowledge_loader.find_drug(normalized_drug_name)
            
            if not drug_data:
                logger.debug(f"Drug '{normalized_drug_name}' not in knowledge base")
                return None
            
            # Build result from medication data
            result = {
                "results": [{
                    "name": drug_data.get("drug_name", normalized_drug_name),
                    "category": drug_data.get("category", ""),
                    "indications": drug_data.get("indications", []),
                    "contraindications": drug_data.get("contraindications", []),
                    "precautions": drug_data.get("precautions", []),
                    "adverse_effects": drug_data.get("adverse_effects", {}),
                    "dose_info": drug_data.get("dose", {}),
                    "interactions": drug_data.get("interactions", []),
                    "source": "Medication knowledge base + RxNorm + FDA API"
                }],
                "count": 1
            }
            
            # Try to add FDA data
            try:
                if self.ani_fda:
                    fda_data = self.ani_fda.get_drug_label(normalized_drug_name)
                    if fda_data and "error" not in fda_data:
                        result["results"][0]["fda_data"] = fda_data
                        logger.info(f"FDA data added for: {normalized_drug_name}")
            except Exception as e:
                logger.debug(f"FDA lookup optional - skipped: {e}")
            
            logger.info(f"Medication query success: {normalized_drug_name}")
            return result
            
        except Exception as e:
            logger.warning(f"Medication query failed: {e}")
            return None
    
    def calculate_medication_dose(self, drug_name, weight_kg, age_years):
        """
        Calculate pediatric medication dose using DoseCalculator
        
        Args:
            drug_name: str (medication name)
            weight_kg: float (patient weight)
            age_years: float (patient age)
        
        Returns:
            dict with dose calculation or error message
        """
        if not self.ani_mcp:
            return {"error": "Medication components not available"}
        
        try:
            # Normalize drug name first
            normalized = self._normalize_drug_name(drug_name)
            if not normalized:
                normalized = drug_name
            
            # Use medication controller to calculate dose
            result = self.ani_mcp.process(
                drug_name=normalized,
                weight_kg=weight_kg,
                age_years=age_years
            )
            
            logger.info(f"Dose calculated: {normalized} {weight_kg}kg {age_years}y")
            return result
            
        except Exception as e:
            logger.error(f"Dose calculation failed: {e}")
            return {"error": str(e)}

    def search_vaccine(self, query_text):
        results = []
        if not self.immunization_db:
            return {"results": results, "count": 0}

        vaccines = self.immunization_db.get("vaccines", [])

        for vaccine in vaccines:
            if (query_text.lower() in vaccine.get("name", "").lower() or
                query_text.lower() in vaccine.get("description", "").lower()):
                results.append(vaccine)

        return {"results": results, "count": len(results)}

    def get_milestone_by_age(self, age_months):
        if not self.milestone_db:
            return {"results": [], "count": 0}

        milestones = self.milestone_db.get("milestones", [])
        results = [m for m in milestones if m.get("age_months") == age_months]

        return {"results": results, "count": len(results)}

    def search_milestone(self, query_text):
        """
        Search milestones with age extraction and semantic matching.
        Parses query like "what milestones should patient reach? (Patient age: 4 years)"
        and returns milestones for that age group.
        """
        results = []
        if not self.milestone_db:
            return {"results": results, "count": 0}

        # Extract age from query (looks for pattern like "(Patient age: 4 years)")
        age_months = None
        import re
        age_match = re.search(r'\(Patient age: (\d+)\s*(?:year|month)s?\)', query_text)
        if age_match:
            age_value = int(age_match.group(1))
            # Convert years to months if necessary
            if age_value < 36:  # Likely in years if less than 36 months (3 years)
                age_months = age_value * 12
            else:
                age_months = age_value
        
        # If we found an age, use query_milestone_db with structured search
        if age_months:
            logger.info(f"Searching milestones for age: {age_months} months")
            return self.query_milestone_db(age_months=age_months)
        
        # Fallback: search by milestone type or keyword matching
        milestones = self.milestone_db.get("milestones", [])
        for milestone in milestones:
            if (query_text.lower() in str(milestone.get("type", "")).lower() or
                any(query_text.lower() in m.lower() for m in milestone.get("milestones", []))):
                results.append(milestone)

        return {"results": results, "count": len(results)}
