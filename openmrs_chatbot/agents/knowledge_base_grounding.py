"""
Knowledge Base Grounding (Phase 1D)
Validates medication answers against available knowledge bases and assigns confidence scores

Features:
- Check if drug information exists in knowledge bases
- Validate answer relevance and accuracy
- Assign confidence scores based on source
- Detect out-of-scope questions
- Provide source attribution
"""

import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KnowledgeBaseGrounding:
    """Ground medication answers in available knowledge bases"""
    
    def __init__(self, kb_path: str = 'openmrs_chatbot/data'):
        """
        Initialize knowledge bases
        
        Args:
            kb_path: Path to knowledge base files
        """
        self.kb_path = Path(kb_path)
        self.medical_drugs = self._load_json('medical_drugs.json')
        self.immunization = self._load_json('immunization.json')
        self.milestones = self._load_json('milestones.json')
        self.responses = self._load_json('responses.json')
        
        # Confidence scores by source
        self.source_confidence = {
            'medical_drugs': 0.95,      # High: curated drug database
            'immunization': 0.90,       # High: vaccine data
            'milestones': 0.85,         # Medium-High: development milestones
            'responses': 0.70,          # Medium: pre-defined responses
            'calculated': 0.60,         # Medium: derived/calculated
            'inferred': 0.50,           # Low: inferred from multiple sources
            'unknown': 0.20,            # Very Low: not in any database
        }
        
        # Scope boundaries - what questions we can answer
        self.answerable_topics = {
            'medication_info': ['uses', 'side_effects', 'warnings', 'dosage_form'],
            'allergies': ['allergy_symptoms', 'cross_reactivity', 'severity'],
            'interactions': ['drug_interaction', 'food_interaction'],
            'pediatric': ['age_appropriate', 'dosage', 'safety'],
            'immunization': ['vaccines', 'schedule', 'contraindications'],
            'milestones': ['developmental', 'age_based'],
        }
        
        # Out-of-scope topics
        self.out_of_scope = [
            'diagnosis',
            'treatment_recommendations',
            'surgical_procedures',
            'psychiatric_conditions',
            'rare_genetic_diseases',
            'research_studies',
            'clinical_trials',
        ]
    
    def _load_json(self, filename: str) -> Dict:
        """Load JSON knowledge base file"""
        filepath = self.kb_path / filename
        
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Knowledge base file not found: {filepath}")
                return {}
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}
    
    def check_drug_in_database(self, drug_name: str) -> Tuple[bool, List[str]]:
        """
        Check if drug exists in medical knowledge base
        
        Args:
            drug_name: Drug name to check
        
        Returns:
            Tuple of (exists: bool, sources: list of sources where found)
        """
        drug_lower = drug_name.lower().strip()
        sources = []
        
        # Check medical_drugs database (has 'drugs' key)
        if self.medical_drugs:
            drugs_list = self.medical_drugs.get('drugs', [])
            if isinstance(drugs_list, list):
                for entry in drugs_list:
                    if isinstance(entry, dict):
                        if entry.get('drug_name', '').lower() == drug_lower:
                            sources.append('medical_drugs')
                            break
        
        # Check if mentioned in responses
        if self.responses and isinstance(self.responses, dict):
            for key in self.responses.keys():
                if drug_lower in key.lower():
                    sources.append('responses')
                    break
        
        return (len(sources) > 0, sources)
    
    def ground_medication_answer(
        self,
        drug_name: str,
        question: str,
        intent: str
    ) -> Dict:
        """
        Ground a medication answer to knowledge bases
        
        Args:
            drug_name: Medication being asked about
            question: Original question
            intent: Question intent (from processor)
        
        Returns:
            Dict with:
            - can_answer: bool
            - confidence: float (0.0-1.0)
            - source: str (where answer comes from)
            - grounding_quality: str (high/medium/low/none)
            - recommendation: str (what to do)
        """
        result = {
            'drug': drug_name,
            'question': question,
            'intent': intent,
            'can_answer': False,
            'confidence': 0.0,
            'source': None,
            'grounding_quality': 'none',
            'recommendation': '',
            'justification': ''
        }
        
        # Check if question is answerable
        if not self._is_question_in_scope(intent):
            result['recommendation'] = 'OUT_OF_SCOPE: Refer to healthcare provider'
            result['justification'] = f'Intent "{intent}" not in answerable scope'
            logger.info(f"[GROUNDING] Out-of-scope intent: {intent}")
            return result
        
        # Check if drug is in database
        exists, sources = self.check_drug_in_database(drug_name)
        
        if not exists:
            result['can_answer'] = False
            result['confidence'] = self.source_confidence['unknown']
            result['source'] = 'none'
            result['grounding_quality'] = 'none'
            result['recommendation'] = (
                'UNKNOWN_DRUG: Lacking knowledge - refer to pharmacist'
            )
            result['justification'] = f'Drug "{drug_name}" not in knowledge base'
            logger.warning(f"[GROUNDING] Drug not found: {drug_name}")
            return result
        
        # Determine confidence based on source
        confidence_scores = [self.source_confidence.get(s, 0.5) for s in sources]
        max_confidence = max(confidence_scores) if confidence_scores else 0.0
        primary_source = sources[0] if sources else 'unknown'
        
        result['can_answer'] = True
        result['confidence'] = max_confidence
        result['source'] = ' + '.join(sources)
        result['grounding_quality'] = self._classify_confidence(max_confidence)
        result['justification'] = (
            f'Drug found in {primary_source} knowledge base'
        )
        
        # Add recommendations based on confidence
        if max_confidence >= 0.85:
            result['recommendation'] = 'ANSWER_WITH_CONFIDENCE'
        elif max_confidence >= 0.60:
            result['recommendation'] = 'ANSWER_WITH_CAUTION'
        else:
            result['recommendation'] = 'SUGGEST_EXPERT_CONSULTATION'
        
        logger.info(
            f"[GROUNDING] {drug_name}: confidence={max_confidence:.2f}, "
            f"source={primary_source}, quality={result['grounding_quality']}"
        )
        
        return result
    
    def _is_question_in_scope(self, intent: str) -> bool:
        """Check if question intent is within answerable scope"""
        answerable_intents = [
            'MEDICATION_LIST',
            'MEDICATION_SAFETY_CHECK',
            'MEDICATION_ALLERGY_CHECK',
            'MEDICATION_INFO',
            'MEDICATION_INTERACTION',
        ]
        
        return intent in answerable_intents
    
    def _classify_confidence(self, confidence: float) -> str:
        """Classify confidence level"""
        if confidence >= 0.85:
            return 'high'
        elif confidence >= 0.60:
            return 'medium'
        elif confidence >= 0.30:
            return 'low'
        else:
            return 'none'
    
    def validate_answer_completeness(
        self,
        drug_name: str,
        answer: str
    ) -> Dict:
        """
        Validate that answer contains sufficient information
        
        Args:
            drug_name: Medication discussed
            answer: Generated answer text
        
        Returns:
            Dict with:
            - is_complete: bool
            - missing_elements: list
            - completeness_score: float (0.0-1.0)
        """
        result = {
            'drug': drug_name,
            'is_complete': True,
            'missing_elements': [],
            'completeness_score': 1.0,
            'quality_checks': {}
        }
        
        answer_lower = answer.lower()
        
        # Essential elements for medication answers
        essential_elements = {
            'uses': ['used for', 'used to', 'treat', 'purpose'],
            'safety': ['safe', 'risk', 'caution', 'warning', 'allerg'],
            'when_to_doctor': ['doctor', 'healthcare', 'medical', 'consultant'],
        }
        
        found_elements = 0
        for element, keywords in essential_elements.items():
            found = any(kw in answer_lower for kw in keywords)
            result['quality_checks'][element] = found
            
            if found:
                found_elements += 1
            else:
                result['missing_elements'].append(element)
        
        # Calculate completeness
        result['completeness_score'] = found_elements / len(essential_elements)
        result['is_complete'] = result['completeness_score'] >= 0.66  # Need 2/3 elements
        
        return result
    
    def detect_evidence_gaps(
        self,
        drug_name: str,
        question: str,
        answer: str
    ) -> Dict:
        """
        Detect gaps between question and available evidence
        
        Args:
            drug_name: Drug being discussed
            question: Original question
            answer: Generated answer
        
        Returns:
            Dict with:
            - gaps_found: int
            - gap_types: list
            - requires_expert_review: bool
            - evidence_quality: str
        """
        result = {
            'drug': drug_name,
            'gaps_found': 0,
            'gap_types': [],
            'requires_expert_review': False,
            'evidence_quality': 'unknown'
        }
        
        # Check if drug is fully documented
        exists, sources = self.check_drug_in_database(drug_name)
        
        if not exists:
            result['gaps_found'] += 1
            result['gap_types'].append('drug_not_in_database')
            result['requires_expert_review'] = True
        
        # Check for pediatric-specific information
        if 'age' in question.lower() or 'child' in question.lower():
            if not any('pediatric' in s.lower() for s in sources):
                result['gaps_found'] += 1
                result['gap_types'].append('missing_pediatric_info')
        
        # Check for allergy information
        if 'allerg' in question.lower():
            if 'medical_drugs' not in sources:
                result['gaps_found'] += 1
                result['gap_types'].append('incomplete_allergy_data')
        
        # Determine evidence quality
        if result['gaps_found'] == 0:
            result['evidence_quality'] = 'high'
        elif result['gaps_found'] == 1:
            result['evidence_quality'] = 'medium'
        else:
            result['evidence_quality'] = 'low'
            result['requires_expert_review'] = True
        
        return result
    
    def ground_complete_query(
        self,
        drug_name: Optional[str],
        question: str,
        intent: str,
        answer: str = ""
    ) -> Dict:
        """
        Complete knowledge base grounding for a query
        
        Args:
            drug_name: Medication (if any)
            question: Original question
            intent: Classified intent
            answer: Generated answer (optional)
        
        Returns:
            Dict with:
            - answerable: bool
            - confidence: float
            - sources: list
            - answer_support: str (strong/moderate/weak)
            - required_disclaimers: list
        """
        result = {
            'question': question,
            'intent': intent,
            'drug': drug_name,
            'answerable': False,
            'confidence': 0.0,
            'sources': [],
            'answer_support': 'none',
            'required_disclaimers': [],
            'grounding_status': 'UNKNOWN'
        }
        
        # Check if intent is in scope
        if not self._is_question_in_scope(intent):
            result['grounding_status'] = 'OUT_OF_SCOPE'
            result['required_disclaimers'].append(
                '[DISCLAIMER] This question is beyond my knowledge base.'
            )
            logger.info(f"[GROUNDING] Out-of-scope intent: {intent}")
            return result
        
        # If no drug specified, mark as general question
        if not drug_name:
            result['answerable'] = True
            result['confidence'] = 0.70
            result['answer_support'] = 'moderate'
            result['grounding_status'] = 'GENERAL_QUESTION'
            result['sources'] = ['general_medical_knowledge']
            return result
        
        # Ground against drug database
        drug_grounding = self.ground_medication_answer(drug_name, question, intent)
        
        result['answerable'] = drug_grounding['can_answer']
        result['confidence'] = drug_grounding['confidence']
        result['sources'] = drug_grounding['source'].split(' + ')
        result['grounding_status'] = drug_grounding['recommendation']
        
        # Classify answer support
        if drug_grounding['confidence'] >= 0.85:
            result['answer_support'] = 'strong'
        elif drug_grounding['confidence'] >= 0.60:
            result['answer_support'] = 'moderate'
        else:
            result['answer_support'] = 'weak'
        
        # Add disclaimers based on confidence
        if drug_grounding['confidence'] < 0.85:
            result['required_disclaimers'].append(
                '[REMINDER] Always consult your healthcare provider for personalized advice.'
            )
        
        if drug_grounding['confidence'] < 0.60:
            result['required_disclaimers'].append(
                '[IMPORTANT] Limited information available. Pharmacist consultation recommended.'
            )
        
        return result
