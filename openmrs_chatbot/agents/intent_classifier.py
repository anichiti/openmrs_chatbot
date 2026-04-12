"""
Intent Classification Module - 3-Layer Hybrid System (DEPRECATED)
This file is deprecated - use two_layer_classifier.py instead.
Uses sentence embeddings + NLI classification for medical query classification
"""

import logging
import time
from typing import Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

# Configure logging
logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    3-layer hybrid intent classifier for medical queries.
    
    Layer 1: Emergency keyword detection (< 5ms)
    Layer 2: Sentence embedding similarity (< 50ms)
    Layer 3: NLI classification (< 100ms)
    """

    # Define intents to classify
    VALID_INTENTS = [
        "MEDICATION_QUERY",
        "MEDICATION_INFO_QUERY",
        "MEDICATION_EMERGENCY",
        "ALLERGY_QUERY",
        "IMMUNIZATION_QUERY",
        "VITALS_QUERY",
        "MILESTONE_QUERY",
        "GENERAL_MEDICAL_QUERY",
        "PATIENT_RECORD_QUERY",
    ]

    # Emergency keywords for Layer 1
    EMERGENCY_KEYWORDS = [
        "overdose",
        "too much",
        "swallowed",
        "poisoning",
        "accidentally took",
        "toxic",
        "too many tablets",
    ]

    def __init__(self):
        """
        Initialize IntentClassifier.
        
        Loads embedding model and pre-computes intent vectors at startup.
        Raises RuntimeError if embedding model fails to load.
        """
        try:
            logger.info("Loading SentenceTransformer model...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Cannot load SentenceTransformer: {e}")

        # Define example sentences for each intent (6-8 examples each)
        self.INTENT_EXAMPLES = {
            "MEDICATION_QUERY": [
                "What is the dosage for paracetamol?",
                "How much amoxicillin should be given?",
                "What's the recommended dose for ibuprofen?",
                "Tell me the dosage of aspirin",
                "What dose of metformin is appropriate?",
                "How many tablets of this drug?",
                "What's the standard dosage?",
                "What is the paracetamol dose for this patient?",
                "What is the safe ibuprofen dose for patient 10000A9?",
                "Calculate the dose for paracetamol",
                "How much mg of this medication?",
                "What is the safe amount of amoxicillin?",
                "What dosage calculation for this child?",
                "How many milligrams per kilogram?",
                "Calculate mg per kg dose",
                "What's the dose in mg for the patient?",
                "What is the ibuprofen dose?",
                "What is the paracetamol dose?",
            ],
            "MEDICATION_INFO_QUERY": [
                "What medications does the patient take?",
                "Can you tell me the patient's current drugs?",
                "What are the active medications for this patient?",
                "Does the patient have any prescribed medicines?",
                "What drugs is the patient on?",
                "Retrieve the medication list for the patient",
                "What medications are in the patient's record?",
                "List all medications in the patient's profile",
                "What medicines is George receiving?",
                "Show me the active drug list",
                "What are the current prescriptions?",
            ],
            "MEDICATION_EMERGENCY": [
                "The patient took an overdose!",
                "My child swallowed too many tablets",
                "There was accidental poisoning",
                "The patient took toxic amounts",
                "Help, overdose situation!",
                "Patient took too much medication",
                "Accidentally consumed excess drugs",
                "My child accidentally took too many doses",
                "George accidentally took too many of his tablets",
            ],
            "ALLERGY_QUERY": [
                "Does the patient have any allergies?",
                "What allergies are documented?",
                "Can the patient take penicillin?",
                "Is the patient allergic to anything?",
                "What drug allergies does this patient have?",
                "Are there any known allergies?",
                "Can my child have amoxicillin?",
                "Is there anything this patient should not be given?",
                "What medications are contraindicated?",
                "Are there any drugs to avoid?",
                "What should we not prescribe?",
                "List patient allergies",
                "Drug sensitivities for patient?",
                "Which drugs cause reactions?",
                "Patient allergic to penicillin?",
                "Any adverse drug reactions?",
                "Medication contraindications?",
                "What is patient allergic to?",
                "Allergy history for this patient?",
                "Safe medications for patient?",
                "Dangerous drugs for patient?",
                "Patient has allergies to?",
                "Any medication allergies documented?",
            ],
            "IMMUNIZATION_QUERY": [
                "What immunizations does the patient need?",
                "Has the patient had their vaccinations?",
                "What vaccines are due for this child?",
                "When is the next vaccine needed?",
                "What's the patient's immunization status?",
                "Which vaccines has the patient received?",
                "When should the next vaccination be?",
            ],
            "VITALS_QUERY": [
                "What's the patient's blood pressure?",
                "What's the patient's weight?",
                "Can you check the patient's temperature?",
                "What are the vital signs?",
                "What's the patient's heart rate?",
                "Show me the patient's BMI",
                "What vital signs are documented?",
                "What is the SpO2?",
                "What is the oxygen saturation?",
                "How heavy is the patient?",
                "How tall is the patient?",
                "What's patient weight in kg?",
                "Check patient height",
                "Is patient overweight?",
                "What is respiratory rate?",
                "Check temperature reading",
                "What's the SpO2 reading?",
                "What's the oxygen level?",
                "How much does the patient weigh?",
                "Patient weight?",
                "Patient height?",
                "How heavy is george?",
                "What are vital measurements?",
                "Show vitals",
                "Patient vital signs?",
                "Blood pressure reading?",
                "Heart rate checking?",
                "Temperature measurement?",
                "Patient measurements?",
                "Vital information?",
                "What was the last recorded temperature for this patient?",
                "Last recorded vital signs?",
                "Most recent blood pressure?",
                "Latest temperature reading?",
                "Last BMI measurement?",
                "Recent vital measurements?",
                "Patient recent vitals?",
            ],
            "MILESTONE_QUERY": [
                "What developmental milestones has the child reached?",
                "Is the child on track for their age?",
                "What milestone checkpoints are expected?",
                "Has the child met developmental goals?",
                "What developmental markers should I track?",
                "Is the child reaching their milestones?",
                "Should the child be walking by now?",
                "Should child be talking at this age?",
                "Is it normal the child is not crawling?",
                "When should a baby start walking?",
                "Are developmental skills on track?",
                "Is baby development normal?",
                "Should child be walking?",
                "What developmental milestones has this patient achieved?",
                "Is child development normal for age?",
                "When should child talk?",
                "Developmental status for child?",
                "Is baby sitting up yet?",
                "When do children walk?",
                "Crawling development timeline?",
                "Motor skill development check?",
                "Speech development milestone?",
                "Social development for age?",
                "Cognitive development timeline?",
                "Child reaching developmental goals?",
                "Early development concerns?",
                "Expected milestones for 12 month old?",
            ],
            "GENERAL_MEDICAL_QUERY": [
                "What is hypertension?",
                "Explain diabetes to me",
                "What causes asthma?",
                "Tell me about common infections",
                "What is pneumonia?",
                "How is fever managed?",
                "What are the symptoms of malaria?",
            ],
            "PATIENT_RECORD_QUERY": [
                "Show me the patient's full record",
                "What information is in the patient's chart?",
                "Can you access the patient database?",
                "What's in the patient's medical history?",
                "Pull up the patient's file",
                "What patient data is available?",
                "Show recent patient encounters",
            ],
        }

        # Pre-compute mean embedding vector for each intent
        logger.info("Computing intent vectors...")
        self.intent_vectors: Dict[str, np.ndarray] = {}
        for intent, examples in self.INTENT_EXAMPLES.items():
            embeddings = self.model.encode(examples, convert_to_numpy=True)
            mean_embedding = np.mean(embeddings, axis=0)
            self.intent_vectors[intent] = mean_embedding
        logger.info(f"Intent vectors computed for {len(self.intent_vectors)} intents")
        
        # Initialize NLI classifier
        self.nli_classifier = NLIClassifier()

    def classify(self, query: str, role: str = "doctor") -> Dict:
        """
        Classify a medical query into one of the predefined intents.
        
        Uses 3-layer hybrid approach:
        1. Emergency keyword detection
        2. Embedding-based similarity
        3. NLI classification
        
        Args:
            query: The medical query string to classify
            role: User role (doctor/patient) for context (default: "doctor")
        
        Returns:
            Dict containing:
                - intent: Classified intent name
                - confidence: Confidence score (0.0-1.0)
                - layer_used: Which layer performed classification (1, 2, or 3)
                - response_time_ms: Time taken to classify
                - needs_llm: Whether LLM was queried
                - llm_unavailable: (optional) True if ollama not available
        """
        start_time = time.time()

        try:
            # STEP 1: Emergency Check
            emergency_result = self._check_emergency(query)
            if emergency_result is not None:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "intent": "MEDICATION_EMERGENCY",
                    "confidence": 1.0,
                    "layer_used": 1,
                    "response_time_ms": round(elapsed_ms, 2),
                    "needs_llm": False,
                }

            # STEP 2: Embedding-based Classification
            embedding_result = self._classify_by_embedding(query)
            if embedding_result["confidence"] >= 0.60:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "intent": embedding_result["intent"],
                    "confidence": embedding_result["confidence"],
                    "layer_used": 2,
                    "response_time_ms": round(elapsed_ms, 2),
                    "needs_llm": False,
                }

            # STEP 3: NLI Classification
            logger.info(f"Embedding confidence {embedding_result['confidence']:.3f} < 0.60, using NLI")
            nli_result = self.nli_classifier.classify(query)
            elapsed_ms = (time.time() - start_time) * 1000

            # Return NLI result if available, otherwise fall back to embedding
            if nli_result is not None:
                nli_result["response_time_ms"] = round(elapsed_ms, 2)
                nli_result["needs_llm"] = False
                return nli_result
            else:
                logger.warning("NLI unavailable, using embedding result")
                return {
                    "intent": embedding_result["intent"],
                    "confidence": embedding_result["confidence"],
                    "layer_used": 2,
                    "response_time_ms": round(elapsed_ms, 2),
                    "needs_llm": False,
                }

        except Exception as e:
            logger.error(f"Classification error: {e}", exc_info=True)
            # Safe fallback
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "intent": "GENERAL_MEDICAL_QUERY",
                "confidence": 0.0,
                "layer_used": 0,
                "response_time_ms": round(elapsed_ms, 2),
                "needs_llm": False,
                "error": str(e),
            }

    def _check_emergency(self, query: str) -> Optional[bool]:
        """
        Check if query contains emergency keywords.
        
        Args:
            query: The query to check
        
        Returns:
            True if emergency keywords found, None otherwise
        """
        query_lower = query.lower()
        for keyword in self.EMERGENCY_KEYWORDS:
            if keyword in query_lower:
                logger.info(f"Emergency keyword detected: '{keyword}'")
                return True
        return None

    def _classify_by_embedding(self, query: str) -> Dict:
        """
        Classify query using embedding similarity.
        
        Args:
            query: The query to classify
        
        Returns:
            Dict with 'intent' and 'confidence' keys
        """
        query_embedding = self.model.encode(query, convert_to_numpy=True)

        # Calculate cosine similarity against all intent vectors
        similarities = {}
        for intent, intent_vector in self.intent_vectors.items():
            similarity = self._cosine_similarity(query_embedding, intent_vector)
            similarities[intent] = similarity

        # Find best matching intent
        best_intent = max(similarities, key=similarities.get)
        best_confidence = similarities[best_intent]

        logger.info(f"Embedding classification: {best_intent} (confidence: {best_confidence:.3f})")
        return {
            "intent": best_intent,
            "confidence": float(best_confidence),
        }

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
        
        Returns:
            Cosine similarity score (0.0-1.0)
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        # Handle zero vectors safely
        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    def _validate_llm_response(self, response: str) -> Optional[str]:
        """
        Validate that LLM response is a known intent.
        
        Args:
            response: The response string from LLM
        
        Returns:
            Valid intent name if found, None otherwise
        """
        cleaned = response.strip().upper()

        # Check exact match
        if cleaned in self.VALID_INTENTS:
            return cleaned

        # Try partial matching (in case LLM adds extra chars)
        for intent in self.VALID_INTENTS:
            if intent in cleaned:
                return intent

        return None
