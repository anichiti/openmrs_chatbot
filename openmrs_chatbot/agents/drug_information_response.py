"""
Drug Information Response Formatter
Formats comprehensive drug information for doctor and patient modes
"""

from utils.logger import setup_logger
import json

logger = setup_logger(__name__)


class DrugInformationResponse:
    """Format comprehensive drug information for display"""
    
    @staticmethod
    def _clean_text(text):
        """Clean HTML and special characters from text"""
        if not text:
            return "Not available"
        
        # Basic HTML cleaning
        text = str(text).replace("<br>", "\n").replace("<br/>", "\n")
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&amp;", "&").replace("&quot;", '"')
        
        # Truncate if too long
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text.strip()
    
    @staticmethod
    def format_targeted(drug_info, question=None):
        """
        Format targeted response - show ONLY what was asked for
        
        Args:
            drug_info: Dict from get_comprehensive_drug_info()
            question: The user's original question
        
        Returns:
            Concise response showing only requested information
        """
        if not drug_info.get("fda_data"):
            return "No information available"
        
        fda = drug_info["fda_data"]
        drug_name = drug_info.get("search_term", "Drug")
        question_lower = (question or "").lower()
        
        # Detect what user asked for
        if any(word in question_lower for word in ["indication", "usage", "used for", "what is"]):
            info = DrugInformationResponse._clean_text(fda.get("indications"))
            return f"{info}" if info != "Not available" else "No indications information available"
        
        elif any(word in question_lower for word in ["side effect", "adverse", "reaction"]):
            info = DrugInformationResponse._clean_text(fda.get("side_effects"))
            return f"{info}" if info != "Not available" else "No side effects information available"
        
        elif any(word in question_lower for word in ["contraindication", "do not use", "when not"]):
            info = DrugInformationResponse._clean_text(fda.get("contraindications"))
            if info == "Not available":
                info = DrugInformationResponse._clean_text(fda.get("do_not_use"))
            return f"{info}" if info != "Not available" else "No contraindication information available"
        
        elif any(word in question_lower for word in ["dosage", "dose", "administration", "how to use"]):
            info = DrugInformationResponse._clean_text(fda.get("dosage"))
            return f"{info}" if info != "Not available" else "No dosage information available"
        
        elif any(word in question_lower for word in ["warning", "precaution"]):
            info = DrugInformationResponse._clean_text(fda.get("warnings"))
            return f"{info}" if info != "Not available" else "No warning information available"
        
        elif any(word in question_lower for word in ["interaction", "interact"]):
            info = DrugInformationResponse._clean_text(fda.get("drug_interactions"))
            return f"{info}" if info != "Not available" else "No interaction information available"
        
        elif any(word in question_lower for word in ["pregnant", "pregnancy", "breastfeed", "nursing"]):
            info = DrugInformationResponse._clean_text(fda.get("pregnancy"))
            return f"{info}" if info != "Not available" else "No pregnancy information available"
        
        elif any(word in question_lower for word in ["stop use", "when to stop"]):
            info = DrugInformationResponse._clean_text(fda.get("stop_use"))
            return f"{info}" if info != "Not available" else "No stop-use information available"
        
        # Default comprehensive view
        return DrugInformationResponse.format_for_doctor(drug_info)
    
    @staticmethod
    def format_for_doctor(drug_info):
        """
        Format comprehensive drug information for doctors
        
        Args:
            drug_info: Dict from get_comprehensive_drug_info()
        
        Returns:
            Formatted drug information string
        """
        if drug_info.get("error"):
            return f"ERROR: Unable to retrieve drug information for '{drug_info.get('search_term')}'"
        
        report = f"COMPREHENSIVE DRUG INFORMATION - DOCTOR VIEW\n"
        report += f"{'='*80}\n\n"
        
        # Header
        search_term = drug_info.get("search_term", "Unknown")
        normalized_name = drug_info.get("normalized_name", search_term)
        rxcui = drug_info.get("rxcui", "N/A")
        
        report += f"Drug Search: {search_term}\n"
        report += f"Normalized Name: {normalized_name}\n"
        report += f"RxNorm ID (RxCUI): {rxcui}\n"
        report += f"{'='*80}\n\n"
        
        # FDA Data
        if drug_info.get("fda_label_status") == "found" and drug_info.get("fda_data"):
            fda = drug_info["fda_data"]
            
            report += "FDA LABEL DATA\n"
            report += f"{'-'*80}\n"
            
            if fda.get("brand_name"):
                report += f"Brand Name: {fda['brand_name']}\n"
            
            if fda.get("generic_name"):
                report += f"Generic Name: {fda['generic_name']}\n"
            
            if fda.get("manufacturer"):
                report += f"Manufacturer: {fda['manufacturer']}\n"
            
            if fda.get("active_ingredients") and fda.get("active_ingredients") != "Not available":
                report += f"Active Ingredient: {fda['active_ingredients']}\n"
            
            report += f"\n[PURPOSE & INDICATIONS]\n"
            if fda.get("purpose") and fda.get("purpose") != "Not available":
                report += f"Purpose: {DrugInformationResponse._clean_text(fda.get('purpose'))}\n"
            indications = DrugInformationResponse._clean_text(fda.get("indications"))
            report += f"Indications: {indications}\n\n"
            
            report += f"[DO NOT USE / CONTRAINDICATIONS]\n"
            do_not_use = DrugInformationResponse._clean_text(fda.get("do_not_use"))
            report += f"{do_not_use}\n\n"
            
            report += f"[SIDE EFFECTS / ADVERSE REACTIONS]\n"
            side_effects = DrugInformationResponse._clean_text(fda.get("side_effects"))
            report += f"{side_effects}\n\n"
            
            report += f"[WHEN TO ASK YOUR DOCTOR]\n"
            ask_doctor = DrugInformationResponse._clean_text(fda.get("ask_doctor"))
            ask_pharmacist = DrugInformationResponse._clean_text(fda.get("ask_doctor_or_pharmacist"))
            if ask_doctor != "Not available":
                report += f"{ask_doctor}\n"
            if ask_pharmacist != "Not available":
                report += f"{ask_pharmacist}\n"
            if ask_doctor == "Not available" and ask_pharmacist == "Not available":
                report += "Not available\n"
            report += "\n"
            
            if fda.get("boxed_warning") and fda.get("boxed_warning") != "Not available":
                report += f"[BLACK BOX WARNING - SERIOUS]\n"
                boxed_warning = DrugInformationResponse._clean_text(fda.get("boxed_warning"))
                report += f"{boxed_warning}\n\n"
            
            report += f"[WARNINGS]\n"
            warnings = DrugInformationResponse._clean_text(fda.get("warnings"))
            report += f"{warnings}\n\n"
            
            if fda.get("stop_use") and fda.get("stop_use") != "Not available":
                report += f"[STOP USE IF]\n"
                stop_use = DrugInformationResponse._clean_text(fda.get("stop_use"))
                report += f"{stop_use}\n\n"
            
            report += f"[PRECAUTIONS]\n"
            precautions = DrugInformationResponse._clean_text(fda.get("precautions"))
            report += f"{precautions}\n\n"
            
            if fda.get("dosage") and fda.get("dosage") != "Not available":
                report += f"[DOSAGE & ADMINISTRATION]\n"
                dosage = DrugInformationResponse._clean_text(fda.get("dosage"))
                report += f"{dosage}\n\n"
            
            report += f"[DRUG INTERACTIONS]\n"
            interactions = DrugInformationResponse._clean_text(fda.get("drug_interactions"))
            report += f"{interactions}\n\n"
            
            report += f"[PREGNANCY & BREASTFEEDING]\n"
            pregnancy = DrugInformationResponse._clean_text(fda.get("pregnancy"))
            report += f"{pregnancy}\n\n"
            
            report += f"[NURSING MOTHERS]\n"
            nursing = DrugInformationResponse._clean_text(fda.get("nursing"))
            report += f"{nursing}\n\n"
        else:
            report += f"FDA Data: Not available (Status: {drug_info.get('fda_label_status')})\n\n"
        
        # Clinical Notes
        report += f"{'='*80}\n"
        report += "CLINICAL NOTES FOR PRESCRIBER:\n"
        report += "  • Verify patient allergies before prescribing\n"
        report += "  • Check for drug interactions with current medications\n"
        report += "  • Review contraindications for patient conditions\n"
        report += "  • Monitor for adverse reactions during treatment\n"
        report += "  • Consider pregnancy/nursing status when applicable\n"
        report += f"  • Reference RxCUI: {rxcui} for clinical decision support\n\n"
        
        report += "Source: FDA OpenFDA API + RxNorm\n"
        
        return report
    
    @staticmethod
    def format_for_patient(drug_info):
        """
        Format comprehensive drug information for patients (simplified)
        
        Args:
            drug_info: Dict from get_comprehensive_drug_info()
        
        Returns:
            Formatted drug information string suitable for patients
        """
        if drug_info.get("error"):
            return f"Sorry, I couldn't find detailed information about '{drug_info.get('search_term')}'.\nPlease consult your doctor or pharmacist."
        
        report = f"About Your Medicine: {drug_info.get('search_term', 'Unknown')}\n"
        report += f"{'='*70}\n\n"
        
        # Normalized name
        normalized_name = drug_info.get("normalized_name")
        if normalized_name and normalized_name != drug_info.get("search_term"):
            report += f"Also known as: {normalized_name}\n\n"
        
        # FDA Data
        if drug_info.get("fda_label_status") == "found" and drug_info.get("fda_data"):
            fda = drug_info["fda_data"]
            
            report += "INFORMATION ABOUT THIS MEDICINE\n"
            report += f"{'-'*70}\n\n"
            
            # What is it used for
            if fda.get("side_effects"):
                report += "WHAT IS IT USED FOR?\n"
                report += "This section is from the official medication guidelines.\n\n"
            
            # Possible side effects
            report += "POSSIBLE SIDE EFFECTS:\n"
            side_effects = DrugInformationResponse._clean_text(fda.get("side_effects"))
            if side_effects != "Not available":
                report += f"{side_effects}\n\n"
            else:
                report += "For detailed side effects, please ask your pharmacist or doctor.\n\n"
            
            # Important warnings
            if fda.get("contraindications") and fda["contraindications"] != "Not available":
                report += "IMPORTANT - WHEN NOT TO TAKE THIS MEDICINE:\n"
                contraindications = DrugInformationResponse._clean_text(fda.get("contraindications"))
                report += f"{contraindications}\n\n"
            
            # Precautions
            if fda.get("precautions") and fda["precautions"] != "Not available":
                report += "THINGS TO BE CAREFUL ABOUT:\n"
                precautions = DrugInformationResponse._clean_text(fda.get("precautions"))
                report += f"{precautions}\n\n"
            
            # Drug interactions
            if fda.get("drug_interactions") and fda["drug_interactions"] != "Not available":
                report += "OTHER MEDICINES - TELL YOUR DOCTOR:\n"
                report += "Tell your doctor about ALL medicines you take. Some medicines may interact.\n\n"
            
            # Pregnancy/Nursing
            if fda.get("pregnancy") and fda["pregnancy"] != "Not available":
                report += "IF YOU ARE PREGNANT OR NURSING:\n"
                pregnancy = DrugInformationResponse._clean_text(fda.get("pregnancy"))
                report += f"{pregnancy}\n\n"
        else:
            report += "Detailed medication information:\n"
            report += "Please ask your pharmacist or doctor for more information.\n\n"
        
        # Patient recommendations
        report += f"{'='*70}\n"
        report += "IMPORTANT REMINDERS:\n"
        report += "  • Always take as prescribed by your doctor\n"
        report += "  • Keep all medicines out of reach of children\n"
        report += "  • Tell your doctor about any allergies\n"
        report += "  • Inform your doctor of all medicines you're taking\n"
        report += "  • Report any unusual side effects to your doctor\n"
        report += "  • Don't stop taking without consulting your doctor\n\n"
        
        report += "Source: FDA Official Medication Information\n"
        
        return report
    
    @staticmethod
    def format_drug_interactions(interactions_data):
        """
        Format drug interactions information
        
        Args:
            interactions_data: Dict from search_drug_interactions()
        
        Returns:
            Formatted drug interactions string
        """
        report = "DRUG INTERACTIONS CHECK\n"
        report += f"{'='*70}\n\n"
        
        status = interactions_data.get("status")
        
        if status == "found":
            interactions = interactions_data.get("interactions", [])
            report += f"ALERT: Found {len(interactions)} potential interaction(s):\n\n"
            
            for interaction in interactions:
                report += f"• {interaction.get('comment', 'Interaction detected')}\n"
                
                # Drug pair information
                for drug in interaction.get("interactionPair", []):
                    drug1 = drug.get("interactionConcept", [{}])[0].get("specialty", "Drug A")
                    drug2 = drug.get("interactionConcept", [])[1].get("specialty", "Drug B") if len(drug.get("interactionConcept", [])) > 1 else "Drug B"
                    severity = drug.get("severity", "Unknown")
                    
                    report += f"  - Severity: {severity}\n"
                
                report += "\n"
        
        elif status == "no_interactions":
            report += "✓ No significant interactions detected between the provided drugs.\n\n"
        
        elif status == "insufficient_drugs":
            report += "Please provide at least 2 drug names to check for interactions.\n\n"
        
        else:
            report += f"Status: {status}\n"
            if interactions_data.get("error"):
                report += f"Error: {interactions_data['error']}\n"
        
        report += f"{'='*70}\n"
        report += "Source: RxNorm Drug Interaction Database\n"
        
        return report
