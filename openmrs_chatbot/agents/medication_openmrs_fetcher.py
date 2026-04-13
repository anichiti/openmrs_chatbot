"""
Medication OpenMRS Fetcher
Retrieves active medications from OpenMRS database for a patient
"""

from database.db import OpenMRSDatabase
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MedicationOpenMRSFetcher:
    """Fetch active medications from OpenMRS database"""
    
    def __init__(self):
        self.db = None
    
    def _resolve_patient_id(self, patient_external_id):
        """
        Resolve patient external ID (e.g., 100008E) to internal ID
        
        Args:
            patient_external_id: External patient ID (e.g., 100008E)
        
        Returns:
            Internal patient ID (integer) or None if not found
        """
        try:
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            
            # Query to find internal patient ID from external ID
            query = '''
            SELECT p.PATIENT_ID 
            FROM patient p
            JOIN patient_identifier pi ON p.PATIENT_ID = pi.PATIENT_ID
            WHERE pi.IDENTIFIER = %s 
            LIMIT 1
            '''
            
            cursor.execute(query, (patient_external_id,))
            result = cursor.fetchone()
            
            if result:
                internal_id = result[0]
                logger.info(f"[MEDICATION] Found patient {patient_external_id} (internal ID: {internal_id})")
                return internal_id
            else:
                logger.warning(f"[MEDICATION] Patient {patient_external_id} not found in system")
                return None
                
        except Exception as e:
            logger.error(f"[MEDICATION] Error resolving patient ID: {e}")
            return None
    
    def get_active_medications(self, patient_id):
        """
        Get all active medications for a patient
        
        Args:
            patient_id: Patient ID (external, e.g., 100008E)
        
        Returns:
            List of active medications with details including indication
        """
        try:
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            # Resolve external ID to internal ID
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return []
            
            cursor = self.db.connection.cursor()
            
            # Query active medications with indication/reason
            # Use AUTO_EXPIRE_DATE as primary indicator (set by OpenMRS based on dosing instructions)
            # Falls back to DATE_STOPPED if AUTO_EXPIRE_DATE is not set
            query = '''
            SELECT 
                o.ORDER_ID,
                o.DATE_ACTIVATED,
                o.DATE_STOPPED,
                do.DRUG_INVENTORY_ID,
                d.NAME as DRUG_NAME,
                do.DOSE,
                do.DOSE_UNITS,
                do.FREQUENCY,
                do.DOSING_INSTRUCTIONS,
                do.ROUTE,
                COALESCE(o.ORDER_REASON_NON_CODED, o.ORDER_REASON) as INDICATION
            FROM orders o
            JOIN drug_order do ON o.ORDER_ID = do.ORDER_ID
            JOIN drug d ON do.DRUG_INVENTORY_ID = d.DRUG_ID
            WHERE o.PATIENT_ID = %s 
            AND o.VOIDED = 0
            AND (
                (o.AUTO_EXPIRE_DATE IS NULL OR o.AUTO_EXPIRE_DATE > NOW())
                AND (o.DATE_STOPPED IS NULL OR o.DATE_STOPPED > NOW())
            )
            ORDER BY o.DATE_ACTIVATED DESC
            '''
            
            cursor.execute(query, (internal_id,))
            results = cursor.fetchall()
            
            medications = []
            for row in results:
                # Convert route to text if it's a number, otherwise use as-is
                route = row[9]
                if isinstance(route, int):
                    route_text = 'Oral'  # Default route for numeric IDs
                else:
                    route_text = str(route) if route else 'Oral'
                
                # Get indication/reason from ORDER_REASON field
                indication = row[10] if row[10] else 'Not specified'
                
                med = {
                    'order_id': row[0],
                    'date_activated': str(row[1]) if row[1] else None,
                    'date_stopped': str(row[2]) if row[2] else None,
                    'drug_id': row[3],
                    'drug_name': row[4],
                    'dose': row[5],
                    'dose_units': row[6],
                    'frequency': row[7],
                    'instructions': row[8],
                    'route': route_text,
                    'indication': indication
                }
                medications.append(med)
            
            logger.info(f"[MEDICATION] Found {len(medications)} active medications for patient {patient_id}")
            return medications
            
        except Exception as e:
            logger.error(f"[MEDICATION] Error fetching active medications: {e}")
            return []
    
    def get_past_medications(self, patient_id):
        """
        Get all discontinued/past medications for a patient
        
        Args:
            patient_id: Patient ID (external, e.g., 100008E)
        
        Returns:
            List of past medications with details
        """
        try:
            if not self.db:
                self.db = OpenMRSDatabase()
                self.db.connect()
            
            # Resolve external ID to internal ID
            internal_id = self._resolve_patient_id(patient_id)
            if not internal_id:
                return []
            
            cursor = self.db.connection.cursor()
            
            # Query past/discontinued medications with indication/reason
            # Use AUTO_EXPIRE_DATE as primary indicator (set by OpenMRS based on dosing instructions)
            # Falls back to DATE_STOPPED if AUTO_EXPIRE_DATE is not set
            query = '''
            SELECT 
                o.ORDER_ID,
                o.DATE_ACTIVATED,
                o.DATE_STOPPED,
                do.DRUG_INVENTORY_ID,
                d.NAME as DRUG_NAME,
                do.DOSE,
                do.DOSE_UNITS,
                do.FREQUENCY,
                do.DOSING_INSTRUCTIONS,
                do.ROUTE,
                COALESCE(o.ORDER_REASON_NON_CODED, o.ORDER_REASON) as INDICATION
            FROM orders o
            JOIN drug_order do ON o.ORDER_ID = do.ORDER_ID
            JOIN drug d ON do.DRUG_INVENTORY_ID = d.DRUG_ID
            WHERE o.PATIENT_ID = %s 
            AND o.VOIDED = 0
            AND (
                (o.AUTO_EXPIRE_DATE IS NOT NULL AND o.AUTO_EXPIRE_DATE <= NOW())
                OR (o.DATE_STOPPED IS NOT NULL AND o.DATE_STOPPED <= NOW())
            )
            ORDER BY COALESCE(o.AUTO_EXPIRE_DATE, o.DATE_STOPPED) DESC
            '''
            
            cursor.execute(query, (internal_id,))
            results = cursor.fetchall()
            
            medications = []
            for row in results:
                # Convert route to text if it's a number, otherwise use as-is
                route = row[9]
                if isinstance(route, int):
                    route_text = 'Oral'  # Default route for numeric IDs
                else:
                    route_text = str(route) if route else 'Oral'
                
                # Get indication/reason from ORDER_REASON field
                indication = row[10] if row[10] else 'Not specified'
                
                med = {
                    'order_id': row[0],
                    'date_activated': str(row[1]) if row[1] else None,
                    'date_stopped': str(row[2]) if row[2] else None,
                    'drug_id': row[3],
                    'drug_name': row[4],
                    'dose': row[5],
                    'dose_units': row[6],
                    'frequency': row[7],
                    'instructions': row[8],
                    'route': route_text,
                    'status': 'Discontinued',
                    'indication': indication
                }
                medications.append(med)
            
            logger.info(f"[MEDICATION] Found {len(medications)} past medications for patient {patient_id}")
            return medications
            
        except Exception as e:
            logger.error(f"[MEDICATION] Error fetching past medications: {e}")
            return []

    def disconnect(self):
        """Close database connection"""
        if self.db:
            self.db.disconnect()
