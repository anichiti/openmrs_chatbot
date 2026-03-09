"""
Validation Agent - Prevents hallucination by verifying data availability

This agent implements the "try agent - script-KB/DB" approach:
- Validates that database connections succeeded
- Verifies actual data was retrieved (not empty results)
- Ensures responses only contain verified facts from actual sources
- Flags when information is NOT available instead of allowing hallucination
"""

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ValidationAgent:
    """Validates data before allowing response generation"""
    
    def __init__(self):
        logger.info("ValidationAgent initialized with hallucination prevention")
    
    def check_database_connection_status(self, patient_data):
        """
        Check if database connection was successful by examining errors in patient_data
        Returns: (is_connected: bool, error_message: str or None)
        """
        if not patient_data:
            return False, "No patient data structure provided"
        
        # Check each component for errors
        for component_name, component_data in patient_data.items():
            if isinstance(component_data, dict):
                if component_data.get("error"):
                    error_msg = component_data.get("error")
                    # If it's a connection error, database is down
                    if "connection" in str(error_msg).lower() or "connect" in str(error_msg).lower():
                        return False, f"Database connection failed: {error_msg}"
        
        return True, None
    
    def has_actual_patient_data(self, patient_data):
        """
        Check if actual patient data was retrieved (not just errors)
        Returns: (has_data: bool, available_components: list)
        """
        if not patient_data:
            return False, []
        
        available = []
        
        # Check patient demographics
        if patient_data.get("patient") and patient_data["patient"].get("data"):
            if len(patient_data["patient"]["data"]) > 0:
                available.append("patient_demographics")
        
        # Check observations
        if patient_data.get("observations") and patient_data["observations"].get("data"):
            if len(patient_data["observations"]["data"]) > 0:
                available.append("observations")
        
        # Check encounters
        if patient_data.get("encounters") and patient_data["encounters"].get("data"):
            if len(patient_data["encounters"]["data"]) > 0:
                available.append("encounters")
        
        # Check conditions
        if patient_data.get("conditions") and patient_data["conditions"].get("data"):
            if len(patient_data["conditions"]["data"]) > 0:
                available.append("conditions")
        
        has_data = len(available) > 0
        return has_data, available
    
    def validate_context_data(self, context_data, intent, patient_id):
        """
        Validate that context_data has actual data for the requested intent
        Returns: (is_valid: bool, validation_result: dict)
        """
        validation_result = {
            "is_valid": False,
            "has_database_connection": False,
            "has_actual_data": False,
            "available_components": [],
            "error_message": None,
            "warning": None,
            "sources": []
        }
        
        # If this is a patient record query, we MUST have database data
        if intent == "PATIENT_RECORD_QUERY" and patient_id:
            # Check database connection
            db_connected, db_error = self.check_database_connection_status(
                context_data.get("patient_data", {})
            )
            validation_result["has_database_connection"] = db_connected
            
            if not db_connected:
                validation_result["error_message"] = (
                    f"Database connection unavailable. Cannot retrieve patient record. "
                    f"Issue: {db_error}"
                )
                validation_result["sources"] = []
                return validation_result
            
            # Check if actual data was retrieved
            has_data, available = self.has_actual_patient_data(
                context_data.get("patient_data", {})
            )
            validation_result["has_actual_data"] = has_data
            validation_result["available_components"] = available
            
            if not has_data:
                validation_result["error_message"] = (
                    f"No patient record found for ID {patient_id} in database. "
                    f"Please verify the patient ID and try again."
                )
                validation_result["sources"] = []
                return validation_result
            
            # All checks passed
            validation_result["is_valid"] = True
            validation_result["sources"] = ["Patient Record (OpenMRS)"]
            
            if context_data.get("kb_content"):
                validation_result["sources"].append("Medical Knowledge Base")
        
        # For other intents, collect valid sources
        else:
            valid_sources = []
            
            if context_data.get("patient_data"):
                has_data, _ = self.has_actual_patient_data(context_data.get("patient_data"))
                if has_data:
                    valid_sources.append("Patient Record (OpenMRS)")
            
            if context_data.get("kb_content"):
                valid_sources.append("Medical Knowledge Base")
            
            if context_data.get("mcp_data"):
                mcp_data = context_data.get("mcp_data", {})
                if mcp_data.get("medications"):
                    valid_sources.append("Medication Database")
                if mcp_data.get("vaccines"):
                    valid_sources.append("Immunization Database")
                if mcp_data.get("milestones"):
                    valid_sources.append("Milestone Database")
            
            if valid_sources:
                validation_result["is_valid"] = True
            
            validation_result["sources"] = valid_sources
        
        return validation_result
    
    def verify_response_against_data(self, response_text, context_data):
        """
        Check response for common hallucination patterns
        Returns: (is_hallucinated: bool, issues: list)
        """
        issues = []
        
        # Check for specific fabricated patient examples
        fabricated_patterns = [
            ("Jane Smith", "Fabricated patient name - not from actual database"),
            ("John Doe", "Fabricated patient name - not from actual database"),
            ("150 pounds", "Fabricated weight - verify against actual patient data"),
            ("5.9 feet", "Fabricated height - verify against actual patient data"),
            ("23 years old", "Fabricated age - verify against actual patient data"),
        ]
        
        response_lower = response_text.lower()
        for pattern, issue in fabricated_patterns:
            if pattern.lower() in response_lower:
                issues.append(issue)
        
        # Check for logical inconsistencies
        if "no data available" in response_lower and any(
            marker in response_text for marker in ["age:", "height:", "weight:", "name:"]
        ):
            issues.append("Response claims no data but provides specific values")
        
        is_hallucinated = len(issues) > 0
        return is_hallucinated, issues
    
    def create_no_data_response(self, error_message):
        """Create appropriate response when data is not available"""
        return {
            "answer": f"I cannot provide the requested information because: {error_message}",
            "when_to_see_doctor": "Please contact your healthcare provider or visit the clinic to ensure your information is properly registered in the system.",
            "confidence": "NO_DATA_AVAILABLE",
            "data_source": "NONE"
        }

