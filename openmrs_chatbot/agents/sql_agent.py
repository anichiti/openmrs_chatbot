import ollama
from database.db import OpenMRSDatabase
from utils.logger import setup_logger
from utils.config import OLLAMA_HOST, OLLAMA_MODEL
import re

logger = setup_logger(__name__)

# Configure Ollama client
ollama_client = ollama.Client(host=OLLAMA_HOST)


class SQLAgent:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.client = ollama_client
        self.db = OpenMRSDatabase()

    def generate_sql_query(self, question, patient_id=None):
        prompt = f"""
Generate a MySQL SELECT query to answer this clinical question.

OpenMRS Schema Reference:
- patient: patient_id, dea_number, voided
- person: person_id, gender, birthdate, dead, death_date
- person_name: person_id, given_name, family_name, voided
- person_address: person_id, address1, address2, city_village, state_province, postal_code, voided
- encounter: encounter_id, patient_id, encounter_type, encounter_datetime, location_id, voided
- encounter_type: encounter_type_id, name
- obs: obs_id, person_id, concept_id, obs_datetime, value_numeric, value_text, value_coded, voided
- concept_name: concept_id, name, locale
- conditions: condition_id, patient_id, condition_coded, onset_date, end_date

Rules:
1. Only SELECT queries allowed
2. Always filter voided=false OR voided=0
3. Use JOINs for related tables
4. Order by most recent datetime DESC
5. Add reasonable LIMIT

Question: {question}
{"Patient ID: " + str(patient_id) if patient_id else ""}

Generate ONLY the SQL query. No explanation.
"""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
            )
            sql_query = response['response'].strip()
            logger.info(f"SQL generated")
            return sql_query
        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")
            return None

    def execute_sql(self, query):
        try:
            if not self.db.connect():
                return {"error": "Database connection failed"}
            
            result = self.db.execute_query(query)
            self.db.disconnect()
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {"error": str(e), "data": None}

    def query_patient_record(self, patient_id):
        """Query comprehensive patient record from OpenMRS
        Accepts both patient_id (internal) and patient_identifier (like 1000001W)
        """
        logger.info(f"Querying patient {patient_id}...")
        
        try:
            if not self.db.connect():
                logger.error("Failed to connect to database for patient query")
                return {
                    "patient": {"error": "Database connection failed", "data": None},
                    "observations": {"error": "Database connection failed", "data": None},
                    "encounters": {"error": "Database connection failed", "data": None},
                    "conditions": {"error": "Database connection failed", "data": None},
                    "vitals": {"error": "Database connection failed", "data": None}
                }
            
            # First, verify patient exists and get internal patient_id if needed
            patient_info = self.db.verify_patient_exists(patient_id)
            if patient_info is None:
                logger.error("Database error during patient verification")
                return {
                    "patient": {"error": "Database connection error", "data": None},
                    "observations": {"error": "Database connection error", "data": None},
                    "encounters": {"error": "Database connection error", "data": None},
                    "conditions": {"error": "Database connection error", "data": None},
                    "vitals": {"error": "Database connection error", "data": None}
                }
            elif patient_info is False:
                logger.warning(f"Patient {patient_id} not found")
                return {
                    "patient": {"error": f"Patient '{patient_id}' not found", "data": None},
                    "observations": {"error": f"Patient '{patient_id}' not found", "data": None},
                    "encounters": {"error": f"Patient '{patient_id}' not found", "data": None},
                    "conditions": {"error": f"Patient '{patient_id}' not found", "data": None},
                    "vitals": {"error": f"Patient '{patient_id}' not found", "data": None}
                }
            
            # Get the internal patient_id
            internal_patient_id = patient_info.get('patient_id')
            logger.info(f"Verified patient ID {patient_id} -> internal ID {internal_patient_id}")
            
            # Get data with proper error handling
            try:
                patient = self.db.get_patient_by_id(internal_patient_id)
            except Exception as e:
                logger.error(f"Error fetching patient: {e}")
                patient = {"error": str(e), "data": None}
            
            try:
                observations = self.db.get_patient_observations(internal_patient_id, limit=50)
            except Exception as e:
                logger.error(f"Error fetching observations: {e}")
                observations = {"error": str(e), "data": None}
            
            try:
                encounters = self.db.get_patient_encounters(internal_patient_id, limit=10)
            except Exception as e:
                logger.error(f"Error fetching encounters: {e}")
                encounters = {"error": str(e), "data": None}
            
            try:
                conditions = self.db.get_patient_conditions(internal_patient_id)
            except Exception as e:
                logger.error(f"Error fetching conditions: {e}")
                conditions = {"error": str(e), "data": None}
            
            try:
                vitals = self.db.get_patient_recent_vitals(internal_patient_id)
            except Exception as e:
                logger.error(f"Error fetching vitals: {e}")
                vitals = {"error": str(e), "data": None}
            
            self.db.disconnect()
            
            return {
                "patient": patient,
                "observations": observations,
                "encounters": encounters,
                "conditions": conditions,
                "vitals": vitals
            }
        except Exception as e:
            logger.error(f"Patient query failed: {str(e)}")
            self.db.disconnect()
            return {
                "patient": {"error": str(e), "data": None},
                "observations": {"error": str(e), "data": None},
                "encounters": {"error": str(e), "data": None},
                "conditions": {"error": str(e), "data": None},
                "vitals": {"error": str(e), "data": None}
            }

    def search_patients(self, name):
        logger.info(f"Searching patients for: {name}")
        try:
            if not self.db.connect():
                return None
            
            results = self.db.search_patients(name, limit=20)
            self.db.disconnect()
            return results
        except Exception as e:
            logger.error(f"Patient search failed: {str(e)}")
            return None
