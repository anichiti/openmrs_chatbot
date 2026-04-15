#!/usr/bin/env python3
"""
SIMPLIFIED 2-LAYER INTENT CLASSIFIER
This replaces the 3-layer (Keywords → Embeddings → NLI) system
with a cleaner 2-layer approach: Keywords → Embeddings

Intents supported:
1. DRUG_INFORMATION_QUERY - Side effects, contraindications, warnings, interactions
2. MEDICATION_QUERY - Doctor asking: what dose of drug X?
3. MEDICATION_INFO_QUERY - What drugs is patient on?
4. MEDICATION_EMERGENCY - Patient overdosed/poisoned
5. ALLERGY_QUERY - Is patient allergic to X? What can't we give?
6. VITALS_QUERY - Blood pressure, weight, temperature, SpO2, etc
7. VITALS_HISTORY_QUERY - Past vital readings, vitals trend, history
8. IMMUNIZATION_QUERY - What vaccines? Vaccination status?
9. LAB_QUERY - Patient lab results and orders?
10. ENCOUNTERS_QUERY - Patient visits and encounters?
11. FUTURE_APPOINTMENTS_QUERY - Upcoming scheduled appointments?
12. MILESTONE_QUERY - Child development - should be walking/talking?
13. PATIENT_RECORD_QUERY - Patient demographics (name, age, DOB)
14. GENERAL_MEDICAL_QUERY - General medical knowledge (not patient-specific)

Flow:
  Layer 1 (Keywords) → If high confidence, return immediately
  Layer 2 (Embeddings) → If Layer 1 < threshold, use sentence similarity
  Default → Return GENERAL_MEDICAL_QUERY
"""

import logging
import re
from typing import Dict, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TwoLayerIntentClassifier:
    """
    Clean 2-layer intent classifier for medical chatbot.
    
    Layer 1: Keyword matching (fast, specific)
    Layer 2: Embedding similarity (accurate for ambiguous cases)
    """

    def __init__(self):
        """Initialize classifier with keywords and embedding model."""
        
        # Layer 1: Keyword patterns for each intent
        # Keywords are domain-specific and highly indicative
        self.INTENT_KEYWORDS = {
            "DRUG_INFORMATION_QUERY": {
                "keywords": [
                    "side effect", "adverse", "warning",
                    "interaction", "pregnant", "pregnancy", "nursing", "breastfeed",
                    "mechanism", "how does.*work", "what causes", "allergy",
                    "reaction", "safe.*pregnant", "safe.*nursing", "safe.*breastfeed",
                    "benefit", "risk", "indication", "pharmacology",
                    "fda approved", "clinical uses", "what is.*used",
                    "metabolism", "elimination", "dosing", "frequency"
                ],
                "weight": 0.9,  # Reduced from 0.95 to match IMMUNIZATION
            },

            "MEDICATION_EMERGENCY": {
                "keywords": [
                    "overdose", "too much", "swallowed", "poison", 
                    "accidentally took", "toxic", "emergency", "help",
                    "extra dose", "double dose", "double the amount",
                    "got into medicine", "medicine cabinet", "pills",
                    "unsure how much", "not sure how much", "ingested"
                ],
                "weight": 1.0,  # High weight - very specific
            },
            
            "MEDICATION_QUERY": {
                "keywords": [
                    "dose", "dosage", "mg", "how much", "how many",
                    "calculate dose", "drug dose", "medication dose",
                    "drug amount", "strength", "potency", "ml",
                    "tablets", "pills", "capsules", "per kg",
                    "safe dose", "correct dose", "right dose"
                ],
                "weight": 0.9,  # Very specific to dose calculation
            },
            
            "MEDICATION_INFO_QUERY": {
                "keywords": [
                    "what drugs", "what medications", "current drugs",
                    "active medications", "prescribed", "is.*on",
                    "taking medications", "drug list", "medication list",
                    "current prescriptions", "list.*medicines"
                ],
                "weight": 0.85,
            },
            
            "PAST_MEDICATIONS_QUERY": {
                "keywords": [
                    "past medications", "previous medications", "old medications",
                    "was.*on", "used to take", "took before", "discontinued",
                    "stopped taking", "former", "previously prescribed",
                    "medication history", "had.*before", "did.*take",
                    "prior medications", "past drugs", "former medications",
                    "what.*was.*on", "medications.*before"
                ],
                "weight": 0.9,
            },
            
            "ALLERGY_QUERY": {
                "keywords": [
                    "allerg", "adverse reaction", "contraindicated",
                    "should not be given", "safe to give", "can.*take",
                    "reaction to", "intolerant", "hypersensitiv",
                    "avoid giving", "can.*have", "reaction",
                    "avoid.*medicine", "avoid.*drug", "avoid.*given",
                    "should.*avoid", "medicines.*avoid", "drugs.*avoid",
                    "what.*avoid", "which.*avoid", "prescribe",
                    "can.*prescribe", "can i give", "can we give",
                    "takes", "take", "happens if", "what if"
                ],
                "weight": 0.9,
            },
            
            "VITALS_QUERY": {
                "keywords": [
                    "blood pressure", "heart rate", "patient.*temperature", "patient.*fever",
                    "pulse", "respiratory", "weight", "height", "bmi",
                    "oxygen", "spo2", "saturation", "vital signs",
                    "how heavy", "how tall", "last recorded", "vital",
                    "current vitals", "latest vitals", "recent vitals"
                ],
                "weight": 0.85,
            },
            
            "VITALS_HISTORY_QUERY": {
                "keywords": [
                    "vitals history", "vital history", "past vitals", "previous vitals",
                    "vitals trend", "vital readings history", "past readings",
                    "vitals summary", "reading history", "how.*vitals.*changed",
                    "vitals over time", "chart.*vitals", "vitals.*past",
                    "last.*vitals", "vitals.*last", "historical vitals"
                ],
                "weight": 0.9,
            },
            
            "IMMUNIZATION_QUERY": {
                "keywords": [
                    "vaccine.*received", "vaccination status", "patient.*vaccine", 
                    "immunization status", "shots.*child", "shots.*patient",
                    "booster", "vaccine due", "vaccination record", "immunized",
                    "shots received", "vaccines given", "up to date",
                    "vaccination history", "immunization history", "did.*get",
                    "immunizations did", "vaccines.*received",
                    "what vaccine", "what vaccines", "next vaccine", "next scheduled",
                    "vaccines due", "due for.*vaccine", "mmr vaccine", "dpt vaccine",
                    "covid.*vaccine", "polio vaccine", "influenza vaccine",
                    "vaccine contraindication", "vaccine contraindications", 
                    "vaccine side effect", "vaccine side effects", "vaccine risk",
                    "vaccine adverse", "vaccine allergy", "vaccine safety",
                    "vaccination schedule", "vaccine schedule", "immunization schedule",
                    "still due", "still needs", "overdue.*vaccine"
                ],
                "weight": 0.95,  # Increased to match DRUG_INFORMATION (removed contraindication from there)
            },
            
            "LAB_QUERY": {
                "keywords": [
                    "lab", "laboratory", "test", "result", "results",
                    "blood test", "x-ray", "imaging", "scan",
                    "culture", "biopsy", "pathology", "serology",
                    "hemoglobin", "glucose", "cholesterol", "triglyceride",
                    "urinalysis", "creatinine", "liver function test",
                    "kidney function", "electrolytes", "albumin",
                    "CBC", "FBC", "analysis", "report",
                    "what are.*results", "show.*results", "test results",
                    "lab results", "lab order", "lab test", "pending test"
                ],
                "weight": 0.88,
            },
            
            "ENCOUNTERS_QUERY": {
                "keywords": [
                    "encounter", "visit", "appointment", "consultation",
                    "clinical visit", "doctor visit", "patient visit",
                    "health encounter", "medical visit", "checkup",
                    "visit history", "encounter history", "past visits",
                    "appointment history", "consultation history",
                    "visited", "came in", "seen at", "attended",
                    "last visit", "recent visit", "previous visit",
                    "encounter type", "reason for visit", "chief complaint",
                    "clinic visit", "hospital visit", "outpatient"
                ],
                "weight": 0.87,
            },
            
            "FUTURE_APPOINTMENTS_QUERY": {
                "keywords": [
                    "future appointment", "upcoming appointment", "next appointment",
                    "scheduled appointment", "next visit", "upcoming visit",
                    "when is appointment", "appointment date", "appointment time",
                    "scheduled visits", "future visits", "upcoming visits",
                    "not yet attended", "not yet happened", "coming up",
                    "future consultation", "upcoming checkup", "scheduled checkup",
                    "appointment schedule", "future schedule", "what's scheduled"
                ],
                "weight": 0.88,
            },
            
            "MILESTONE_QUERY": {
                "keywords": [
                    "milestone", "development", "developmental",
                    "walking", "talking", "crawling", "sitting",
                    "achieving", "reached", "skill", "ability",
                    "should.*be", "normal for age", "speaking",
                    "expected to", "months old"
                ],
                "weight": 0.85,
            },
            
            "PATIENT_RECORD_QUERY": {
                "keywords": [
                    "patient name", "date of birth", "birthdate", "age",
                    "gender", "address", "phone", "demographics",
                    "patient info", "patient details", "who is",
                    "how old", "basic details", "patient record"
                ],
                "weight": 0.8,
            },
        }
        
        # Layer 2: Example sentences for embedding-based similarity
        # These help the embedding model understand intent when keywords don't match
        self.INTENT_EXAMPLES = {
            "DRUG_INFORMATION_QUERY": [
                "What are the side effects of amoxicillin?",
                "Tell me about adverse reactions to aspirin",
                "Is ibuprofen safe during pregnancy?",
                "Drug interactions with metformin?",
                "Contraindications for antibiotics",
                "What precautions with this medication?",
                "FDA approved uses for the drug?",
            ],

            "MEDICATION_EMERGENCY": [
                "Patient urgent overdose help needed",
                "Child accidentally took too much medicine",
                "Emergency toxic substance poisoning",
                "Patient took excess drug amount",
            ],
            
            "MEDICATION_QUERY": [
                "What is the dose of paracetamol?",
                "Calculate ibuprofen dosage for child",
                "How much amoxicillin to give?",
                "What's the recommended drug dose?",
                "Drug dosing calculation needed",
            ],
            
            "MEDICATION_INFO_QUERY": [
                "What medications is the patient taking?",
                "List current prescriptions",
                "What drugs is patient on?",
                "Current active medications?",
                "Patient medication history",
            ],
            
            "PAST_MEDICATIONS_QUERY": [
                "What medications was the patient on before?",
                "What past medications did patient take?",
                "Discontinued medications history?",
                "What medications were previously prescribed?",
                "Patient's former medication list?",
                "What drugs did patient used to take?",
            ],
            
            "ALLERGY_QUERY": [
                "Does patient have any allergies?",
                "Is this drug safe for patient?",
                "What medications are contraindicated?",
                "Patient allergic to penicillin?",
                "Drug adverse reactions documented?",
                "What medicines should my child avoid?",
                "Which drugs should we avoid giving?",
            ],
            
            "VITALS_QUERY": [
                "What is patient blood pressure?",
                "Patient weight and height?",
                "Check vital signs",
                "What's the temperature reading?",
                "What is SpO2?",
                "Current vitals?",
            ],
            
            "VITALS_HISTORY_QUERY": [
                "What is the patient's vitals history?",
                "Show me past vital readings?",
                "Vitals trend over time?",
                "Historical vital signs?",
                "What were the past vitals?",
                "Vital signs readings history?",
            ],
            
            "IMMUNIZATION_QUERY": [
                "What vaccines has patient received?",
                "Vaccination status?",
                "Which shots are due?",
                "Immunization history?",
                "Next vaccine needed?",
            ],
            
            "LAB_QUERY": [
                "What are the patient's lab results?",
                "Show me blood test results",
                "Lab orders placed for patient?",
                "What tests are pending?",
                "Patient lab test results?",
                "Show laboratory analysis",
            ],
            
            "ENCOUNTERS_QUERY": [
                "What are the patient's visits?",
                "Show me patient encounters",
                "Patient visit history?",
                "When was the last visit?",
                "Patient appointment history?",
                "Show clinical encounters",
            ],
            
            "FUTURE_APPOINTMENTS_QUERY": [
                "What are the patient's upcoming appointments?",
                "Show me future scheduled appointments",
                "When is the next appointment?",
                "What appointments does patient have?",
                "Upcoming appointments schedule?",
                "Future visits scheduled?",
            ],
            
            "MILESTONE_QUERY": [
                "Is child reaching developmental milestones?",
                "Should child be walking by now?",
                "Normal development for age?",
                "Child development status?",
                "Achieved developmental goals?",
                "When should a baby start crawling?",
                "When should my child start speaking?",
                "What milestones should my baby reach by 12 months?",
            ],
            
            "PATIENT_RECORD_QUERY": [
                "What is patient age?",
                "Patient date of birth?",
                "Patient demographics?",
                "Basic patient information?",
                "Patient name and details?",
            ],
        }
        
        # Initialize embedding model for Layer 2
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Pre-compute embedding vectors for each intent's examples
        self.intent_vectors: Dict[str, np.ndarray] = {}
        self._compute_intent_vectors()
        
        logger.info("✓ 2-Layer Intent Classifier initialized successfully")
    
    def _compute_intent_vectors(self):
        """Pre-compute mean embedding vectors for each intent."""
        logger.info("Computing intent embedding vectors...")
        
        for intent, examples in self.INTENT_EXAMPLES.items():
            embeddings = self.embedding_model.encode(examples, convert_to_numpy=True)
            mean_vector = np.mean(embeddings, axis=0)
            self.intent_vectors[intent] = mean_vector
        
        logger.info(f"✓ Computed vectors for {len(self.intent_vectors)} intents")
    
    def classify(self, query: str) -> Dict:
        """
        Classify query into intent using 2-layer approach.
        
        Args:
            query: User question to classify
        
        Returns:
            Dict with keys:
                - intent: Classified intent name
                - confidence: Confidence score (0.0-1.0)
                - layer_used: 1 or 2 (which layer made the decision)
        """
        
        query_lower = query.lower().strip()
        
        # ============================================================
        # LAYER 1: Keyword Matching (Fast, High Confidence)
        # ============================================================
        layer1_scores = self._keyword_layer(query_lower)
        
        if layer1_scores:
            best_intent = max(layer1_scores.items(), key=lambda x: x[1])
            intent_name, score = best_intent
            
            if score >= 0.1:  # Even 1 keyword match is significant for medical domain
                logger.debug(f"[Layer 1] {intent_name} (score: {score:.3f})")
                return {
                    "intent": intent_name,
                    "confidence": score,
                    "layer_used": 1,
                }
        
        # ============================================================
        # LAYER 2: Embedding Similarity (Accurate, for edge cases)
        # ============================================================
        layer2_result = self._embedding_layer(query_lower)
        
        if layer2_result["confidence"] > 0.55:  # Embedding threshold
            logger.debug(f"[Layer 2] {layer2_result['intent']} (score: {layer2_result['confidence']:.3f})")
            return {
                "intent": layer2_result["intent"],
                "confidence": layer2_result["confidence"],
                "layer_used": 2,
            }
        
        # ============================================================
        # FALLBACK: Generic medical question
        # ============================================================
        logger.debug(f"[Fallback] No strong match, using GENERAL_MEDICAL_QUERY")
        return {
            "intent": "GENERAL_MEDICAL_QUERY",
            "confidence": 0.0,
            "layer_used": 0,
        }
    
    def _keyword_layer(self, query_lower: str) -> Dict[str, float]:
        """
        Layer 1: Score query against keyword patterns.
        
        Better scoring: keywords are weighted individually (not normalized by count).
        This way, finding 1 critical keyword gives a strong signal.
        
        Returns dict of {intent: score}
        """
        scores = {}
        
        for intent, config in self.INTENT_KEYWORDS.items():
            keyword_score = 0
            matched_keywords = 0
            
            # Score based on keyword matches found
            for keyword in config["keywords"]:
                # Handle regex patterns
                if "*" in keyword or ".*" in keyword:
                    if re.search(keyword, query_lower):
                        matched_keywords += 1
                        keyword_score += 0.15  # Each keyword match adds 0.15
                else:
                    if keyword in query_lower:
                        matched_keywords += 1
                        keyword_score += 0.15  # Each keyword match adds 0.15
            
            # Cap at 0.95 and apply intent weight
            if keyword_score > 0:
                keyword_score = min(keyword_score, 0.95)  # Don't let it exceed 0.95
                scores[intent] = keyword_score * config["weight"]
        
        return scores
    
    def _embedding_layer(self, query_lower: str) -> Dict:
        """
        Layer 2: Use embedding similarity to score query.
        
        Returns dict with intent, confidence
        """
        # Encode the query
        query_embedding = self.embedding_model.encode(query_lower, convert_to_numpy=True)
        
        best_intent = None
        best_score = 0.0
        
        # Compare against each intent's vector
        for intent, intent_vector in self.intent_vectors.items():
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, intent_vector)
            
            if similarity > best_score:
                best_score = similarity
                best_intent = intent
        
        return {
            "intent": best_intent or "GENERAL_MEDICAL_QUERY",
            "confidence": float(best_score),
        }
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


if __name__ == "__main__":
    # Test the classifier
    classifier = TwoLayerIntentClassifier()
    
    test_queries = [
        "What is the paracetamol dose for a 5kg child?",
        "Patient overdosed on medicine help!",
        "What medications is patient on?",
        "Does patient have allergies?",
        "What is blood pressure?",
        "Has patient been vaccinated?",
        "Should child be walking?",
        "What is patient age?",
        "Tell me about diabetes",
    ]
    
    print("\n" + "="*80)
    print("TESTING 2-LAYER CLASSIFIER")
    print("="*80 + "\n")
    
    for query in test_queries:
        result = classifier.classify(query)
        layer = "L1: Keywords" if result["layer_used"] == 1 else "L2: Embedding" if result["layer_used"] == 2 else "Fallback"
        print(f"Query: {query}")
        print(f"Intent: {result['intent']} | Confidence: {result['confidence']:.3f} | {layer}\n")
