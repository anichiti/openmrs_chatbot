import mysql.connector
from mysql.connector import Error
from utils.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OpenMRSDatabase:
    def __init__(self):
        self.host = DB_HOST
        self.port = DB_PORT
        self.database = DB_NAME
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.connection = None
        
    def connect(self):
        """Connect directly to MySQL OpenMRS database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                autocommit=True
            )
            logger.info("OpenMRS database connected")
            return True
        except Error as e:
            logger.error(f"OpenMRS database connection failed: {str(e)}")
            return False

    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("OpenMRS database disconnected")

    def is_query_safe(self, query):
        """Enforce read-only access by blocking destructive queries"""
        forbidden_keywords = ['DELETE', 'UPDATE', 'INSERT', 'DROP', 'ALTER', 'TRUNCATE']
        query_upper = query.upper().strip()
        for keyword in forbidden_keywords:
            if query_upper.startswith(keyword):
                return False
        return True

    def execute_query(self, query, params=None):
        """Execute a read-only query"""
        if not self.connection:
            logger.info("Connecting to database...")
            if not self.connect():
                return {"error": "Database connection failed", "data": None}

        if not self.is_query_safe(query):
            logger.error("Blocked destructive query attempt")
            return {"error": "Read-only access only. Destructive queries forbidden.", "data": None}

        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            logger.info(f"Query retrieved {len(results)} records")
            return {"error": None, "data": results}
        except Error as e:
            logger.error(f"Query failed: {str(e)}")
            return {"error": str(e), "data": None}

    def get_patient_by_id(self, patient_id):
        query = """
        SELECT p.patient_id, pi.identifier as patient_identifier, per.gender, per.birthdate, per.dead, per.death_date,
               pn.given_name, pn.family_name,
               pa.address1, pa.address2, pa.city_village, pa.state_province, pa.postal_code
        FROM patient p
        JOIN person per ON p.patient_id = per.person_id
        LEFT JOIN patient_identifier pi ON p.patient_id = pi.patient_id AND pi.voided = false
        LEFT JOIN person_name pn ON p.patient_id = pn.person_id AND pn.voided = false
        LEFT JOIN person_address pa ON p.patient_id = pa.person_id AND pa.voided = false
        WHERE p.patient_id = %s AND p.voided = false
        LIMIT 1
        """
        return self.execute_query(query, (patient_id,))

    def get_patient_observations(self, patient_id, limit=100):
        query = """
        SELECT o.obs_id, o.person_id, o.concept_id, o.obs_datetime,
               o.value_numeric, o.value_text, o.value_coded,
               cn.name as concept_name
        FROM obs o
        LEFT JOIN concept_name cn ON o.concept_id = cn.concept_id
        WHERE o.person_id = %s AND o.voided = false
        ORDER BY o.obs_datetime DESC
        LIMIT %s
        """
        return self.execute_query(query, (patient_id, limit))

    def get_patient_encounters(self, patient_id, limit=100):
        query = """
        SELECT e.encounter_id, e.patient_id, e.encounter_type, e.encounter_datetime,
               e.location_id, et.name as encounter_type_name
        FROM encounter e
        LEFT JOIN encounter_type et ON e.encounter_type = et.encounter_type_id
        WHERE e.patient_id = %s AND e.voided = false
        ORDER BY e.encounter_datetime DESC
        LIMIT %s
        """
        return self.execute_query(query, (patient_id, limit))

    def get_patient_conditions(self, patient_id):
        query = """
        SELECT c.condition_id, c.patient_id, c.condition_coded, c.onset_date,
               c.end_date, cn.name as condition_name
        FROM conditions c
        LEFT JOIN concept_name cn ON c.condition_coded = cn.concept_id
        WHERE c.patient_id = %s
        ORDER BY c.onset_date DESC
        """
        return self.execute_query(query, (patient_id,))

    def get_patient_vitals(self, patient_id, limit=20):
        """Get vital signs for patient (height, weight, BP, temperature, BMI, etc.)"""
        # OpenMRS concept IDs for common vital signs
        # These are standard concepts in OpenMRS
        query = """
        SELECT o.obs_id, o.person_id, o.concept_id, o.obs_datetime,
               o.value_numeric, o.value_text, o.value_coded,
               cn.name as concept_name, cn.locale
        FROM obs o
        LEFT JOIN concept_name cn ON o.concept_id = cn.concept_id
        WHERE o.person_id = %s 
        AND o.voided = false
        AND cn.name IN ('Height (cm)', 'Weight (kg)', 'Systolic Blood Pressure', 
                        'Diastolic Blood Pressure', 'Temperature (C)', 'Blood Pressure',
                        'Height', 'Weight', 'BP', 'Temp', 'BMI', 'Body Mass Index',
                        'Body mass index', 'BMI (kg/m2)', 'BMI (kg/m²)',
                        'Pulse', 'Heart Rate', 'Heart rate', 'Pulse Rate',
                        'Respiratory Rate', 'Respiratory rate', 'Respiration Rate',
                        'Blood Oxygen Saturation', 'Oxygen Saturation', 'SpO2',
                        'Arterial blood oxygen saturation (pulse oximeter)',
                        'Head Circumference', 'Head circumference (cm)',
                        'Mid-Upper Arm Circumference', 'MUAC')
        ORDER BY o.obs_datetime DESC
        LIMIT %s
        """
        return self.execute_query(query, (patient_id, limit))

    def get_patient_recent_vitals(self, patient_id):
        """Get most recent vital signs for patient (one per vital type), including calculated BMI"""
        query = """
        SELECT cn.name as vital_name, o.value_numeric, o.value_text, o.obs_datetime
        FROM obs o
        JOIN concept_name cn ON o.concept_id = cn.concept_id
        WHERE o.person_id = %s 
        AND o.voided = false
        AND cn.name IN ('Height (cm)', 'Weight (kg)', 'Systolic Blood Pressure', 
                        'Diastolic Blood Pressure', 'Temperature (C)', 'Blood Pressure',
                        'Height', 'Weight', 'BP', 'Temp', 'BMI', 'Body Mass Index',
                        'Body mass index', 'BMI (kg/m2)', 'BMI (kg/m²)',
                        'Pulse', 'Heart Rate', 'Heart rate', 'Pulse Rate',
                        'Respiratory Rate', 'Respiratory rate', 'Respiration Rate',
                        'Blood Oxygen Saturation', 'Oxygen Saturation', 'SpO2',
                        'Arterial blood oxygen saturation (pulse oximeter)',
                        'Head Circumference', 'Head circumference (cm)',
                        'Mid-Upper Arm Circumference', 'MUAC')
        AND o.obs_datetime = (
            SELECT MAX(o2.obs_datetime) 
            FROM obs o2 
            JOIN concept_name cn2 ON o2.concept_id = cn2.concept_id
            WHERE o2.person_id = o.person_id 
            AND cn2.name = cn.name
            AND o2.voided = false
        )
        """
        return self.execute_query(query, (patient_id,))

    def verify_patient_exists(self, patient_id):
        """Verify if a patient ID exists in the database and return full patient details
        Accepts both internal patient_id and patient_identifier (e.g., 1000001W)
        """
        # First try as internal patient_id (numeric)
        try:
            internal_id = int(patient_id)
            query = """
            SELECT p.patient_id, pi.identifier as patient_identifier, pn.given_name, pn.family_name, 
                   per.gender, per.birthdate, per.dead, per.death_date,
                   pa.address1, pa.address2, pa.city_village, pa.state_province, pa.postal_code
            FROM patient p
            LEFT JOIN patient_identifier pi ON p.patient_id = pi.patient_id AND pi.voided = false
            LEFT JOIN person_name pn ON p.patient_id = pn.person_id AND pn.voided = false
            LEFT JOIN person per ON p.patient_id = per.person_id
            LEFT JOIN person_address pa ON p.patient_id = pa.person_id AND pa.voided = false
            WHERE p.patient_id = %s AND p.voided = false
            LIMIT 1
            """
            result = self.execute_query(query, (internal_id,))
            if result.get("error"):
                return None  # Database error
            
            patients = result.get("data", [])
            if patients:
                return patients[0]  # Patient exists
        except (ValueError, TypeError):
            pass  # Not numeric, try as identifier
        
        # Try as patient_identifier (alphanumeric like 1000001W)
        query = """
        SELECT p.patient_id, pi.identifier as patient_identifier, pn.given_name, pn.family_name,
               per.gender, per.birthdate, per.dead, per.death_date,
               pa.address1, pa.address2, pa.city_village, pa.state_province, pa.postal_code
        FROM patient p
        LEFT JOIN patient_identifier pi ON p.patient_id = pi.patient_id AND pi.voided = false
        LEFT JOIN person_name pn ON p.patient_id = pn.person_id AND pn.voided = false
        LEFT JOIN person per ON p.patient_id = per.person_id
        LEFT JOIN person_address pa ON p.patient_id = pa.person_id AND pa.voided = false
        WHERE pi.identifier = %s AND p.voided = false
        LIMIT 1
        """
        result = self.execute_query(query, (patient_id,))
        if result.get("error"):
            return None  # Database error
        
        patients = result.get("data", [])
        if patients:
            return patients[0]  # Patient exists
        
        return False  # Patient does not exist

    def get_patient_age(self, patient_id):
        """Get patient age in years calculated from birthdate"""
        try:
            from datetime import date
            
            query = """
            SELECT per.birthdate
            FROM person per
            WHERE per.person_id = %s AND per.voided = false
            """
            result = self.execute_query(query, (patient_id,))
            
            if result.get("error") or not result.get("data"):
                logger.warning(f"Could not retrieve birthdate for patient {patient_id}")
                return None
            
            birthdate = result["data"][0].get("birthdate")
            if not birthdate:
                logger.warning(f"No birthdate found for patient {patient_id}")
                return None
            
            # Calculate age from birthdate
            today = date.today()
            if isinstance(birthdate, date):
                age = today.year - birthdate.year
                if (today.month, today.day) < (birthdate.month, birthdate.day):
                    age -= 1
            else:
                # If birthdate is a string, parse it
                from datetime import datetime
                birthdate_obj = datetime.strptime(str(birthdate), "%Y-%m-%d").date()
                age = today.year - birthdate_obj.year
                if (today.month, today.day) < (birthdate_obj.month, birthdate_obj.day):
                    age -= 1
            
            logger.info(f"Calculated age for patient {patient_id}: {age} years")
            return age
        except Exception as e:
            logger.error(f"Error calculating patient age: {str(e)}")
            return None

    def search_patients(self, name, limit=20):
        query = """
        SELECT p.patient_id, pi.identifier as patient_identifier, pn.given_name, pn.family_name, 
               per.gender, per.birthdate,
               pa.address1, pa.address2, pa.city_village, pa.state_province, pa.postal_code
        FROM patient p
        LEFT JOIN patient_identifier pi ON p.patient_id = pi.patient_id AND pi.voided = false
        LEFT JOIN person_name pn ON p.patient_id = pn.person_id AND pn.voided = false
        LEFT JOIN person per ON p.patient_id = per.person_id
        LEFT JOIN person_address pa ON p.patient_id = pa.person_id AND pa.voided = false
        WHERE (pn.given_name LIKE %s OR pn.family_name LIKE %s)
        AND p.voided = false
        LIMIT %s
        """
        search_term = f"%{name}%"
        return self.execute_query(query, (search_term, search_term, limit))

    def list_all_patients(self, limit=20):
        """List all patients"""
        query = """
        SELECT p.patient_id, pi.identifier as patient_identifier, pn.given_name, pn.family_name, 
               per.gender, per.birthdate,
               pa.address1, pa.address2, pa.city_village, pa.state_province, pa.postal_code
        FROM patient p
        LEFT JOIN patient_identifier pi ON p.patient_id = pi.patient_id AND pi.voided = false
        LEFT JOIN person_name pn ON p.patient_id = pn.person_id AND pn.voided = false
        LEFT JOIN person per ON p.patient_id = per.person_id
        LEFT JOIN person_address pa ON p.patient_id = pa.person_id AND pa.voided = false
        WHERE p.voided = false
        ORDER BY p.patient_id
        LIMIT %s
        """
        return self.execute_query(query, (limit,))

    def execute_custom_query(self, query):
        return self.execute_query(query)
