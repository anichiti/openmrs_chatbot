import ollama
from utils.logger import setup_logger
from utils.config import OLLAMA_HOST, OLLAMA_MODEL
import json
import time
from datetime import datetime

logger = setup_logger(__name__)

# Configure Ollama client with connection retry
class OllamaClientWrapper:
    def __init__(self, host=OLLAMA_HOST):
        self.host = host
        self.client = None
        self.connect()
    
    def connect(self):
        """Connect to Ollama with retries"""
        try:
            self.client = ollama.Client(host=self.host)
            return True
        except Exception as e:
            logger.warning(f"Ollama connection failed: {e}")
            return False
    
    def generate(self, *args, **kwargs):
        """Generate with Ollama, return None if unavailable"""
        try:
            if not self.client:
                self.connect()
            
            result = self.client.generate(*args, **kwargs)
            return result
        except (KeyboardInterrupt, TimeoutError):
            logger.warning("Ollama request timed out or interrupted")
            return None
        except Exception as e:
            logger.warning(f"Ollama generation failed: {e}")
            return None

ollama_client = OllamaClientWrapper(host=OLLAMA_HOST)


class ResponseAgent:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.client = ollama_client
    
    def calculate_age_from_birthdate(self, birthdate_str):
        """Calculate patient age in years from birthdate string or date object (YYYY-MM-DD)"""
        try:
            if not birthdate_str or birthdate_str == 'N/A':
                return None
            
            # Handle date objects directly
            if hasattr(birthdate_str, 'year'):  # It's a date or datetime object
                birthdate = birthdate_str
                today = datetime.now().date()
                if hasattr(today, 'year'):  # Make sure today is a date object
                    age = today.year - birthdate.year
                    if (today.month, today.day) < (birthdate.month, birthdate.day):
                        age -= 1
                    return age
            
            # Handle string format
            birthdate = datetime.strptime(str(birthdate_str).split()[0], '%Y-%m-%d')
            today = datetime.now()
            age = today.year - birthdate.year
            
            # Adjust if birthday hasn't occurred this year
            if (today.month, today.day) < (birthdate.month, birthdate.day):
                age -= 1
            
            return age
        except Exception as e:
            logger.warning(f"Failed to calculate age from {birthdate_str}: {e}")
            return None

    def calculate_bmi(self, weight_kg, height_cm):
        """Calculate BMI from weight (kg) and height (cm)
        BMI = weight (kg) / (height (m))^2
        """
        try:
            if not weight_kg or not height_cm or weight_kg <= 0 or height_cm <= 0:
                return None
            height_m = height_cm / 100.0
            bmi = weight_kg / (height_m ** 2)
            return round(bmi, 1)
        except Exception as e:
            logger.warning(f"Failed to calculate BMI: {e}")
            return None

    def _is_english_text(self, text):
        """
        Filter for English-only medical terms.
        Uses pattern matching for known non-English medical terms and patterns.
        Rejects anything that looks like it's from French, Spanish, Italian, German, Dutch, etc.
        """
        if not text:
            return False
        
        text = text.strip()
        text_lower = text.lower()
        
        # Step 1: Reject if contains non-ASCII characters (accented letters)
        for char in text:
            if ord(char) > 127:  # Non-ASCII
                return False
        
        # Step 2: Check for known English vital/measurement terms (BEFORE language check)
        # These are common English medical measurements in standard formats
        vital_terms = ['height', 'weight', 'temperature', 'blood pressure', 'systolic', 'diastolic',
                       'heart rate', 'pulse', 'respiratory', 'oxygen', 'spo2', 'glucose', 'bmi', 'body mass index']
        if any(term in text_lower for term in vital_terms):
            return True
        
        # Step 2b: EXTENSIVE non-English indicator patterns (ASCII-only, no accents)
        non_english_indicators = [
            # French patterns
            'tion', 'eux', 'euse', 'ette', 'ment', 'du ', 'de ', ' de ', 'le ', 'les ', 'la ', 'aucun', 
            'mouvement', 'foetus', 'embryo', 'maladies', 'asthenie', 'anemie', 'amenorrhee', 'dysmenorrhee',
            'pneumonie', 'bronchite', 'fievre', 'nausee', 'cilindre', 'urinaire', 'hyalin',
            'temperature', 'hauteur',  # French vital terms
            # Spanish patterns
            'cion', 'idad', 'o ', ' o ', 'a ', ' a ', 'el ', 'los ', 'una ', 'unas ', 'uno ', 'dolor', 
            'enfermedad', 'caries', 'taquipnea', 'debilidad', 'anemia', 'amenorrea', 'dismenorrea',
            'disnea', 'neumon', 'bronqu', 'fiebre', 'nausea', 'cilindro', 'ario', 'articular', 'difuso',
            'temperatura', 'altura',  # Spanish vital terms
            # Italian patterns
            'ario', 'aria', 'ione', 'il ', 'lo ', 'gli ', 'ipertensione', 'asimmetria', 'cilindro',
            'temperatura', 'altezza',  # Italian vital terms
            # German patterns
            'heit', 'keit', 'ung', 'liche', 'ische', 'tachypnoe', 'schwache', 'fieber', 'kopfschmerz', 'schwindel',
            'temperatur',  # German vital terms
            # Dutch patterns
            'aandoening', 'zwakheid', 'koorts', 'hoofdpijn', 'duizeligheid', 'infectieuze',
            # Portuguese patterns
            'ade', 'idade', 'mente', 'peso', 'pressao', 'taquipneia', 'fraqueza', 'febre', 'tontura',
            'temperatura',  # Portuguese vital terms
            # Turkish patterns
            'jitis', 'jit',
            # Haitian Creole patterns
            'enfektyez', 'pa ', 'vini', 'mouvman', 'kote', 'pib', 'reg ',
            # Common multilingual medical term patterns that indicate non-English
            'cylindre', 'tubercul', 'hepat', 'nephro', 'gastro', 'cardio', 'pneumo', 'dermat', 'neuro',
            'maladi', 'enfermedad', 'infectieuze', 'anadoening',
        ]
        
        # Check if any non-English indicator is present
        for pattern in non_english_indicators:
            if pattern in text_lower:
                # Exception: Allow "infection", "conditions", "inflammation" (English medical terms)
                if pattern == 'infect' and ('infection' in text_lower or 'infectious' in text_lower):
                    if 'maladies' in text_lower or 'enfermedad' in text_lower or 'maladi' in text_lower:
                        return False
                    continue
                # Exception: Allow "pregnancy" related (English term)
                if pattern == 'preg' and 'pregnancy' in text_lower:
                    continue
                return False
        
        # Step 3: Require known English medical term patterns for diagnosis terms
        common_english_medical = [
            'pain', 'fever', 'cough', 'cold', 'infection', 'disease', 'disorder',
            'syndrome', 'cancer', 'diabetes', 'asthma', 'emphysema',
            'pneumonia', 'bronchitis', 'hepatitis', 'nephritis', 'meningitis',
            'arthritis', 'dermatitis', 'gastritis', 'enteritis', 'colitis',
            'ulcer', 'allergy', 'eczema', 'psoriasis', 'urticaria', 'anemia',
            'failure', 'hypertension', 'hypotension', 'dysrhythmia', 'arrhythmia',
            'sprain', 'strain', 'fracture', 'dislocation', 'contusion',
            'dizziness', 'vertigo', 'headache', 'migraine', 'nausea', 'vomiting',
            'diarrhea', 'constipation', 'dyspepsia', 'reflux', 'indigestion',
            'fatigue', 'weakness', 'lethargy', 'malaise', 'insomnia', 'sleep',
            'anxiety', 'depression', 'psychosis', 'dementia', 'amnesia',
            'tremor', 'rigidity', 'bradykinesia', 'dyskinesia', 'movement',
            'cast', 'calculus', 'polyuria', 'crepitus', 'murmur', 'wheeze',
            'rash', 'lesion', 'wound', 'burn', 'bleed', 'hemorrhage',
            'joint', 'bone', 'muscle', 'nerve', 'vessel', 'organ', 'system',
            'resolved', 'diagnosis', 'caries', 'dental', 'teeth',
            'tinnitus', 'hearing', 'vision', 'blindness', 'deafness',
            'urinate', 'frequency', 'incontinence', 'retention', 'dysuria',
            'amenorrhea', 'dysmenorrhea', 'menstrual', 'pregnancy', 'delivery',
            'leishmaniasis', 'typhoid', 'malaria', 'cholera', 'typhus',
            'salmonella', 'shigella', 'streptococcus', 'staphylococcus',
            'tuberculosis', 'leprosy', 'fungal', 'viral', 'bacterial', 'parasitic',
            'immunodeficiency', 'hiv', 'aids', 'sepsis', 'endocarditis', 'abscess',
        ]
        
        text_words = text_lower.replace(',', ' ').replace('(', ' ').replace(')', ' ').split()
        has_english_marker = any(eng_word in ' '.join(text_words) for eng_word in common_english_medical)
        
        # Special cases: allow these short English phrases
        if text_lower in ['problem resolved', 'diagnosis resolved', 'removed diagnosis', 'remove diagnosis', 'resolved']:
            return True
        
        # Accept if it has English medical terminology
        if has_english_marker:
            return True
        
        # Reject if it's a multi-word term without English markers (likely non-English)
        if len(text_words) >= 2:
            return False
        
        # Single English words that are common medical terms - accept
        if text_lower in ['allergies', 'asthma', 'diabetes', 'cancer', 'pain', 'fever', 'hypertension']:
            return True
        
        # Default: reject unless proven English
        return False

    def generate_medication_response_with_context(self, question, context_data):
        """Generate medication dose response with patient clinical context for doctors"""
        mcp_data = context_data.get("mcp_data", {})
        med_results = mcp_data.get("medications", {})
        patient_data = context_data.get("patient_data", {})
        sources = context_data.get("sources", [])
        
        response_parts = []
        response_parts.append("Answer:")
        
        # Extract relevant patient information
        patient_weight_kg = None
        patient_age = None
        
        if patient_data.get("vitals") and patient_data["vitals"].get("data"):
            for vital in patient_data["vitals"]["data"]:
                vital_name = vital.get('vital_name', '').lower()
                if 'weight' in vital_name and 'kg' in vital_name.lower():
                    patient_weight_kg = vital.get('value_numeric')
                    if patient_weight_kg:
                        response_parts.append(f"\nPATIENT WEIGHT: {patient_weight_kg} kg")
                        break
        
        if patient_data.get("patient") and patient_data["patient"].get("data"):
            p = patient_data["patient"]["data"][0]
            birthdate = p.get('birthdate')
            if birthdate:
                patient_age = self.calculate_age_from_birthdate(birthdate)
                if patient_age:
                    response_parts.append(f"PATIENT AGE: {patient_age} years")
        
        # Medication and dose information
        if med_results.get("dose_calculation"):
            dose_info = med_results["dose_calculation"]
            response_parts.append(f"\nRECOMMENDED DOSE:")
            if isinstance(dose_info, dict):
                for key, value in dose_info.items():
                    response_parts.append(f"  - {key}: {value}")
            else:
                response_parts.append(f"  - {dose_info}")
        
        # Medication details
        if med_results.get("results") and len(med_results["results"]) > 0:
            med_info = med_results["results"][0]
            med_name = med_info.get("name", "Medication")
            response_parts.append(f"\nMEDICATION: {med_name}")
            
            if med_info.get("description"):
                response_parts.append(f"DESCRIPTION: {med_info.get('description')}")
            if med_info.get("common_indications"):
                response_parts.append(f"INDICATIONS: {med_info.get('common_indications')}")
        
        # Patient clinical context for decision-making
        clinical_context = self.extract_clinical_context(patient_data)
        if clinical_context:
            response_parts.append(f"\nCLINICAL CONTEXT:")
            response_parts.append(clinical_context)
        
        # Warnings/considerations
        response_parts.append("\nCONSIDERATIONS:")
        response_parts.append("- Always verify dose against current clinical guidelines")
        response_parts.append("- Check for patient allergies and contraindications")
        response_parts.append("- Monitor for adverse effects")
        
        response_parts.append("\nConfidence: HIGH")
        
        return "\n".join(response_parts)

    def extract_clinical_context(self, patient_data):
        """Extract relevant clinical context for medication decisions
        Used when doctor asks for dose - shows conditions, recent symptoms, vitals
        """
        if not patient_data:
            return ""
        
        context = []
        
        # Recent vital signs
        if patient_data.get("vitals") and patient_data["vitals"].get("data"):
            context.append("RECENT VITALS:")
            for vital in patient_data["vitals"]["data"][:3]:
                vital_name = vital.get('vital_name', 'Unknown')
                value = vital.get('value_numeric', vital.get('value_text', 'N/A'))
                context.append(f"  - {vital_name}: {value}")
        
        # Recent conditions/diagnoses
        if patient_data.get("conditions") and patient_data["conditions"].get("data"):
            conditions = patient_data["conditions"]["data"][:5]
            if conditions:
                context.append("\nCURRENT CONDITIONS:")
                for cond in conditions:
                    cond_name = cond.get('condition_name', 'Unknown')
                    context.append(f"  - {cond_name}")
        
        # Recent observations (symptoms/findings)
        if patient_data.get("observations") and patient_data["observations"].get("data"):
            obs_list = patient_data["observations"]["data"][:3]
            if obs_list:
                context.append("\nRECENT OBSERVATIONS:")
                for obs in obs_list:
                    concept = obs.get('concept_name', 'Unknown')
                    value = obs.get('value_numeric', obs.get('value_text', 'N/A'))
                    context.append(f"  - {concept}: {value}")
        
        return "\n".join(context)

    def detect_question_intent(self, question):
        """
        Analyze the question to determine what specific information is being asked for.
        Returns a dict with flags for what to include in the response.
        """
        if not question:
            return {"include_all": True}
        
        question_lower = question.lower()
        intent = {"include_all": False}
        
        # Detect what the user is asking for
        if any(word in question_lower for word in ['name', 'called', 'named']):
            intent['name'] = True
        if any(word in question_lower for word in ['age', 'old', 'how old', 'born']):
            intent['age'] = True
        if any(word in question_lower for word in ['weight', 'how heavy', 'weighs']):
            intent['weight'] = True
        if any(word in question_lower for word in ['height', 'tall', 'how tall']):
            intent['height'] = True
        if any(word in question_lower for word in ['bmi', 'body mass index', 'body mass']):
            intent['bmi'] = True
        if any(word in question_lower for word in ['gender', 'sex', 'male', 'female']):
            intent['gender'] = True
        if any(word in question_lower for word in ['vital', 'temperature', 'pressure', 'bp', 'heart rate', 'respiratory']):
            intent['vitals'] = True
        if any(word in question_lower for word in ['condition', 'disease', 'diagnosis', 'health problem', 'suffering']):
            intent['conditions'] = True
        if any(word in question_lower for word in ['encounter', 'visit', 'appointment', 'visited', 'met']):
            intent['encounters'] = True
        if any(word in question_lower for word in ['observation', 'test', 'result', 'lab', 'analysis']):
            intent['observations'] = True
        if any(word in question_lower for word in ['info', 'detail', 'demographic', 'profile', 'tell me about']):
            intent['include_all'] = True
        
        # If asking for something general, include all
        if any(word in question_lower for word in ['what is', 'show me', 'give me']):
            # If it's a vague question without specific keywords, include all
            if sum(1 for k, v in intent.items() if k != 'include_all' and v) == 0:
                intent['include_all'] = True
        
        return intent

    def format_patient_data_for_llm(self, patient_data, question=None):
        """Format structured patient data into readable text for LLM
        If question is provided, filters response to only include relevant information"""
        if not patient_data:
            return "No patient data available."
        
        # Detect what the question is asking for
        intent = self.detect_question_intent(question)
        include_all = intent.get('include_all', False)
        
        formatted = []
        calculated_age = None
        
        # Patient demographics
        if patient_data.get("patient") and patient_data["patient"].get("data"):
            p = patient_data["patient"]["data"][0]
            
            # Only show demographics header if asking for multiple things or everything
            if include_all or sum(1 for k, v in intent.items() if k != 'include_all' and v) > 2:
                formatted.append("PATIENT DEMOGRAPHICS:")
            
            # Patient Identifier
            patient_id = p.get('patient_identifier', p.get('patient_id', 'N/A'))
            
            # Patient Name - include if asked or showing all
            given_name = p.get('given_name', 'N/A')
            family_name = p.get('family_name', 'N/A')
            full_name = f"{given_name} {family_name}".strip()
            if (include_all or intent.get('name')) and full_name and full_name != "N/A N/A":
                formatted.append(f"Name: {full_name}")
            
            # Gender - include if asked
            if include_all or intent.get('gender'):
                formatted.append(f"Gender: {p.get('gender', 'N/A')}")
            
            # Birthdate and Age - include if asked
            birthdate = p.get('birthdate', 'N/A')
            if birthdate != 'N/A':
                if hasattr(birthdate, 'strftime'):
                    birthdate = birthdate.strftime('%Y-%m-%d')
                else:
                    birthdate = str(birthdate)
            
            calculated_age = self.calculate_age_from_birthdate(birthdate)
            if include_all or intent.get('age'):
                if calculated_age is not None:
                    formatted.append(f"Age: {calculated_age} years")
                elif include_all:
                    formatted.append(f"Birth Date: {birthdate}")
            
            # Address - only if showing all
            if include_all:
                formatted.append(f"Address: {p.get('address1', 'N/A')}, {p.get('city_village', 'N/A')}")
            
            if formatted and len(formatted) > 1:
                formatted.append("")  # Add spacing
        
        # Continue with other sections only if asking for them or include_all
        if not include_all and not any([intent.get('vitals'), intent.get('weight'), intent.get('height'), intent.get('bmi')]):
            # Skip vitals section
            pass
        elif patient_data.get("vitals") and patient_data["vitals"].get("data"):
            vitals_list = patient_data["vitals"]["data"]
            if vitals_list:
                found_vitals = False
                vitals_text = []
                seen_vitals = {}
                height_cm = None
                weight_kg = None
                bmi_found = False
                
                for vital in vitals_list:
                    vital_name = vital.get('vital_name', 'Unknown')
                    
                    # Skip if not English
                    if not self._is_english_text(vital_name):
                        continue
                    
                    vital_key = vital_name.lower().strip()
                    if vital_key in seen_vitals:
                        continue
                    seen_vitals[vital_key] = True
                    
                    # Track height and weight for BMI calculation
                    if 'height' in vital_key and vital.get('value_numeric'):
                        height_cm = vital.get('value_numeric')
                    if 'weight' in vital_key and vital.get('value_numeric'):
                        weight_kg = vital.get('value_numeric')
                    
                    # Track if BMI is already in vitals
                    if 'bmi' in vital_key:
                        bmi_found = True
                    
                    # Check if this vital is what was asked for
                    asked_for_this = (include_all or 
                                     intent.get('vitals') or
                                     (intent.get('weight') and 'weight' in vital_key) or
                                     (intent.get('height') and 'height' in vital_key) or
                                     (intent.get('bmi') and 'bmi' in vital_key))
                    
                    if asked_for_this:
                        found_vitals = True
                        value_numeric = vital.get('value_numeric')
                        value_text = vital.get('value_text')
                        date = vital.get('obs_datetime', 'N/A')
                        
                        if value_numeric is not None:
                            vitals_text.append(f"  {vital_name}: {value_numeric} ({date})")
                        elif value_text:
                            vitals_text.append(f"  {vital_name}: {value_text} ({date})")
                
                # Calculate and add BMI if not found but we have height and weight
                # And user is asking for vitals or specifically for BMI
                if (include_all or intent.get('vitals') or intent.get('bmi')) and not bmi_found and height_cm and weight_kg:
                    bmi_value = self.calculate_bmi(weight_kg, height_cm)
                    if bmi_value:
                        vitals_text.append(f"  BMI (calculated): {bmi_value} kg/m2")
                        if intent.get('bmi'):  # If specifically asking for BMI
                            found_vitals = True
                
                if found_vitals and vitals_text:
                    # Only show "VITAL SIGNS" header if showing multiple vitals or all vitals
                    # For single vital like BMI, show it more directly
                    if intent.get('bmi') and len(vitals_text) == 1 and 'bmi' in vitals_text[0].lower():
                        formatted.extend(vitals_text)
                    else:
                        formatted.append("VITAL SIGNS (Most Recent):")
                        formatted.extend(vitals_text)
                    formatted.append("")
        
        # Recent observations - only if asked for
        if not include_all and not intent.get('observations'):
            pass
        elif patient_data.get("observations") and patient_data["observations"].get("data"):
            obs_list = patient_data["observations"]["data"][:5]
            if obs_list:
                obs_text = []
                seen_obs = {}
                
                for obs in obs_list:
                    concept = obs.get('concept_name', 'Unknown')
                    
                    if not self._is_english_text(concept):
                        continue
                    
                    obs_key = concept.lower().strip()
                    if obs_key in seen_obs:
                        continue
                    seen_obs[obs_key] = True
                    
                    value = obs.get('value_numeric') or obs.get('value_text', 'N/A')
                    date = obs.get('obs_datetime', 'N/A')
                    obs_text.append(f"  {concept}: {value} ({date})")
                
                if obs_text:
                    formatted.append("RECENT OBSERVATIONS (last 5):")
                    formatted.extend(obs_text)
                    formatted.append("")
        
        # Encounters - only if asked for
        if not include_all and not intent.get('encounters'):
            pass
        elif patient_data.get("encounters") and patient_data["encounters"].get("data"):
            enc_list = patient_data["encounters"]["data"][:3]
            if enc_list:
                enc_text = []
                seen_enc = {}
                
                for enc in enc_list:
                    enc_type = enc.get('encounter_type_name', 'Unknown')
                    
                    if not self._is_english_text(enc_type):
                        continue
                    
                    enc_key = enc_type.lower().strip()
                    if enc_key in seen_enc:
                        continue
                    seen_enc[enc_key] = True
                    
                    date = enc.get('encounter_datetime', 'N/A')
                    enc_text.append(f"  {enc_type} on {date}")
                
                if enc_text:
                    formatted.append("RECENT ENCOUNTERS (last 3):")
                    formatted.extend(enc_text)
                    formatted.append("")
        
        # Conditions - only if asked for
        if not include_all and not intent.get('conditions'):
            pass
        elif patient_data.get("conditions") and patient_data["conditions"].get("data"):
            cond_list = patient_data["conditions"]["data"]
            if cond_list:
                formatted.append("PATIENT CONDITIONS:")
                seen_conditions = {}
                
                for cond in cond_list:
                    name = cond.get('condition_name', 'Unknown').strip()
                    onset = cond.get('onset_date', 'N/A')
                    
                    is_likely_english = self._is_english_text(name)
                    
                    base_name = name.split('(')[0].strip() if '(' in name else name
                    key = base_name.lower()
                    
                    if is_likely_english and key not in seen_conditions:
                        seen_conditions[key] = True
                        formatted.append(f"  {name}")
        
        return "\n".join(formatted)

    def _clean_response(self, response_text):
        """Clean response by aggressively removing hallucinated content"""
        if not response_text:
            return ""
        
        text = response_text.strip()
        
        # AGGRESSIVE MARKERS for non-medical content
        non_medical_markers = [
            "\nRules of the Puzzle",
            "\nRules:",
            "\nThe goal of",
            "\nHere are some hints",
            "\nThis logic-based puzzle",
            "Consider ",
            "\nConsider",
            "\nUse ",
            "\nUsing ",
            "\nThink",
            "\nAssuming",
            "To calculate",
            "to calculate",
            "subtract their",
            "subtract the",
            "This will give",
            "Therefore, the",
            "Using this calculation",
            "By calculating",
        ]
        
        for marker in non_medical_markers:
            if marker in text:
                idx = text.find(marker)
                if idx > 0:
                    text = text[:idx].strip()
                    break
        
        # Remove lines with gaming/puzzle language
        lines = text.split('\n')
        cleaned_lines = []
        skip_rest = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Stop processing at puzzle/game content
            if any(skip in line_lower for skip in [
                'rules of the puzzle',
                'the goal of',
                'here are some hints',
                'logic-based puzzle',
                'patient alice',
                'patient bob',
                'patient charlie',
                'inspired by',
                'the game is'
            ]):
                skip_rest = True
                continue
            
            # Skip numbered puzzle hints
            if skip_rest or any(f'{i}. ' in line_lower for i in range(1, 7)):
                if line.strip() and not line_lower.startswith('when to see'):
                    continue
            
            # Skip lines that are clearly non-medical
            if any(x in line_lower for x in [
                'Consider',
                'suppose',
                'imagine',
                'hypothetical'
            ]):
                continue
                
            cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        # Clean up multiple newlines
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result

    def generate_doctor_response(self, question, context_data):
        """Generate response for doctor queries with STRICT hallucination prevention"""
        sources = context_data.get("sources", [])
        kb_content = context_data.get("kb_content", "")
        patient_data_raw = context_data.get("patient_data", {})
        
        # Format patient data properly
        patient_data_formatted = self.format_patient_data_for_llm(patient_data_raw)
        
        # Check if we actually have patient data
        has_patient_data = patient_data_formatted and len(patient_data_formatted) > 10
        
        # Limit content to most recent for speed - more generous for doctors
        if len(patient_data_formatted) > 1500:
            patient_data_formatted = patient_data_formatted[:1500] + "\n[... data truncated ...]"
        if len(kb_content) > 500:
            kb_content = kb_content[:500] + "\n[... knowledge base truncated ...]"

        # Build prompt with explicit instructions
        data_status = "PATIENT DATA AVAILABLE" if has_patient_data else "NO PATIENT DATA IN SYSTEM"
        
        prompt = f"""You are a clinical decision support system. You MUST ONLY report ACTUAL FACTS from the provided medical record.

INSTRUCTION LEVEL CRITICAL:
- ONLY use information that appears in the provided patient data section
- If information is NOT in the data, you MUST explicitly say "This information is not available in the patient record"
- Do NOT infer, calculate, guess, or assume values NOT in the data
- Do NOT provide examples or hypothetical scenarios
- Do NOT make up patient demographics like ages, names, or vital signs

DATA AVAILABILITY STATUS: {data_status}

Doctor's Question: {question}

VERIFIED PATIENT MEDICAL DATA:
{patient_data_formatted if has_patient_data else "NO PATIENT DATA AVAILABLE IN SYSTEM"}

MEDICAL KNOWLEDGE REFERENCE:
{kb_content if kb_content else "General information only"}

RESPONSE REQUIREMENTS:
1. Answer ONLY using the provided verified data above
2. If data is not available, clearly state "This information is not available in the patient record"
3. Do NOT invent or simulate patient information
4. Report exactly what is shown in the data section

Your response:"""

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
            )
            if response and response.get('response'):
                logger.info("Response generated for doctor")
                cleaned = self._clean_response(response['response'])
                if not cleaned:
                    cleaned = response['response'].strip()
                return f"Answer:\n{cleaned}\n\nConfidence: MEDIUM"
            else:
                logger.warning("Ollama returned empty response")
                return self._get_fallback_response("doctor", patient_data_raw, sources)
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return self._get_fallback_response("doctor", patient_data_raw, sources)

    def generate_patient_response(self, question, context_data):
        """Generate response for patient queries - patient viewing their OWN medical data"""
        kb_content = context_data.get("kb_content", "")
        patient_data_raw = context_data.get("patient_data", {})
        sources = context_data.get("sources", [])
        
        # Format patient data if available (patients have full access to their own data)
        patient_data_formatted = self.format_patient_data_for_llm(patient_data_raw) if patient_data_raw else ""
        
        # Limit content for faster inference with smaller model
        if len(kb_content) > 400:
            kb_content = kb_content[:400] + "\n[... content truncated ...]"
        if len(patient_data_formatted) > 600:
            patient_data_formatted = patient_data_formatted[:600] + "\n[... data truncated ...]"

        # Build prompt with patient data - EMPHASIZE this is the patient's own data
    def generate_patient_response(self, question, context_data):
        """Generate response for patient queries - STRICT HALLUCINATION PREVENTION"""
        kb_content = context_data.get("kb_content", "")
        patient_data_raw = context_data.get("patient_data", {})
        sources = context_data.get("sources", [])
        
        # Format patient data if available (patients have full access to their own data)
        patient_data_formatted = self.format_patient_data_for_llm(patient_data_raw) if patient_data_raw else ""
        has_patient_data = patient_data_formatted and len(patient_data_formatted) > 10
        
        # Limit content for faster inference with smaller model
        if len(kb_content) > 400:
            kb_content = kb_content[:400] + "\n[... content truncated ...]"
        if len(patient_data_formatted) > 600:
            patient_data_formatted = patient_data_formatted[:600] + "\n[... data truncated ...]"

        # Build prompt with patient data - EMPHASIZE this is the patient's own data
        data_status = "PATIENT DATA AVAILABLE" if has_patient_data else "NO PATIENT DATA IN SYSTEM"
        
        prompt = f"""You are a patient health assistant explaining medical information to patients.

INSTRUCTION LEVEL CRITICAL - YOU MUST FOLLOW THESE RULES:
1. ONLY use information that appears in the provided medical record
2. If information is NOT in the record, you MUST say "This information is not in your medical record"
3. Do NOT infer, calculate, guess, or assume values NOT in the record
4. Do NOT create patient scenarios, examples, or what-if scenarios
5. Do NOT make up health information to "be helpful"
6. NEVER provide specific health values (age, weight, BP, etc.) unless they're in the record

DATA STATUS: {data_status}

Patient's Question: {question}

YOUR MEDICAL RECORD:
{patient_data_formatted if has_patient_data else "NO MEDICAL RECORD DATA IN THE SYSTEM - Please contact your clinic to register."}

GENERAL HEALTH INFORMATION:
{kb_content if kb_content else "General wellness information"}

YOUR RESPONSE MUST:
1. Use ONLY information from your medical record shown above
2. Never invent or simulate personal health information
3. Clearly state when information is not available in your record
4. Direct patients to contact their healthcare provider for missing information

Your response:"""

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
            )
            if response and response.get('response'):
                logger.info("Response generated for patient")
                resp_text = response['response'].strip()
                cleaned = self._clean_response(resp_text)
                if not cleaned:
                    cleaned = resp_text
                return f"Answer:\n{cleaned}\n\nWhen to See Doctor:\nConsult a healthcare provider if symptoms persist or for any health concerns.\n\nConfidence: MEDIUM"
            else:
                logger.warning("Ollama returned empty response")
                return self._get_fallback_response("patient", patient_data_raw, sources)
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return self._get_fallback_response("patient", patient_data_raw, sources)

    def _get_fallback_response(self, user_type, patient_data=None, sources=None):
        """Generate appropriate fallback response based on available data"""
        if user_type.upper() == "DOCTOR":
            # For doctors, provide structured response with what we have
            response_parts = []
            response_parts.append("Answer:")
            
            if patient_data and (patient_data.get("observations") and patient_data["observations"].get("data")):
                obs_count = len(patient_data["observations"].get("data", []))
                response_parts.append(f"Found {obs_count} recent observations for this patient.")
            elif patient_data and (patient_data.get("encounters") and patient_data["encounters"].get("data")):
                enc_count = len(patient_data["encounters"].get("data", []))
                response_parts.append(f"Found {enc_count} recent encounters for this patient.")
            else:
                response_parts.append("Unable to generate a full clinical response at this time.")
            
            response_parts.append("\nData Sources:")
            if sources:
                for source in sources:
                    response_parts.append(f"  - {source}")
            else:
                response_parts.append("  - Limited data available")
            
            response_parts.append("\nConfidence: LOW")
            response_parts.append("\nNote: For complete clinical decision support, please review the patient EHR directly.")
            return "\n".join(response_parts)
        else:
            # For patients, simple guidance
            return """Answer:
I don't have enough verified information to answer your question fully.

Home Care:
For immediate health concerns, follow any guidance from your healthcare provider.

When to See Doctor:
Contact your healthcare provider if:
- Your symptoms worsen
- You develop new or unusual symptoms  
- You have questions about your health

Confidence: LOW

Note: Always consult a healthcare professional for medical advice."""

    def validate_response_safety(self, response, user_type):
        """Check if response contains appropriate confidence markers"""
        if not response:
            return False
        
        response_lower = response.lower()
        # For doctors, should have some data reference
        if user_type.upper() == "DOCTOR":
            has_data = any(word in response_lower for word in ['observation', 'encounter', 'data', 'analysis'])
            return has_data or 'insufficient' in response_lower
        
        # For patients, should have safety guidance
        return 'healthcare' in response_lower or 'doctor' in response_lower or 'provider' in response_lower

    def generate_milestone_response(self, question, context_data, user_type="DOCTOR"):
        """Generate response for milestone queries with patient age context"""
        milestone_data = context_data.get("mcp_data", {}).get("milestones", {})
        patient_age = milestone_data.get("patient_age")
        milestone_results = milestone_data.get("results", [])
        patient_data = context_data.get("patient_data", {})
        
        # Format milestone data for display
        milestone_text = ""
        if milestone_results:
            for milestone_group in milestone_results:
                age_months = milestone_group.get("age_months", 0)
                mtype = milestone_group.get("type", "Unknown")
                milestones_list = milestone_group.get("milestones", [])
                
                milestone_text += f"\n{mtype} Milestones (Age {age_months} months):\n"
                for m in milestones_list:
                    milestone_text += f"  • {m}\n"
        
        # Get patient name if available
        patient_name = "the patient"
        if patient_data.get("patient") and patient_data["patient"].get("data"):
            p = patient_data["patient"]["data"][0]
            given_name = p.get('given_name', '')
            family_name = p.get('family_name', '')
            full_name = f"{given_name} {family_name}".strip()
            if full_name:
                patient_name = full_name
        
        # Build response with patient context for doctors, patient-friendly for patients
        # Case-insensitive comparison for user_type
        if user_type and user_type.upper() == "DOCTOR":
            response_text = f"""PATIENT: {patient_name}
AGE: {patient_age} years ({patient_age * 12} months)

DEVELOPMENTAL MILESTONES:
{milestone_text if milestone_text else "Limited milestone data available for this age group."}

CLINICAL ASSESSMENT:
Based on the patient's age ({patient_age} years), the milestones listed above are typical developmental expectations. Monitor for any significant delays or concerns in these areas during clinical assessment.
"""
        else:
            response_text = f"""Hello {patient_name},

Here are the developmental milestones you should be working towards at {patient_age} years old:
{milestone_text if milestone_text else "Limited milestone data available for this age group."}

TIPS FOR HEALTHY DEVELOPMENT:
• Engage in regular play and social interaction
• Encourage learning through age-appropriate activities
• Maintain regular check-ups with your healthcare provider
• Report any concerns about development to your doctor

If you have concerns about your child's development, please consult with your healthcare provider.
"""
        
        return response_text

