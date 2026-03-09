#!/usr/bin/env python3
"""
Hybrid Question Detector & Router
==================================

Handles questions that ask for BOTH safety AND dosage information.
Example: "Is aspirin safe for my child? How much can I give?"

This is the KEY missing piece - questions are rarely just ONE type.
"""

import re
from typing import Tuple, List, Dict

class HybridQuestionDetector:
    """Detect and route hybrid medical questions"""
    
    # Keywords for each query type
    SAFETY_KEYWORDS = [
        'safe', 'allergic', 'allergy', 'contraindicated', 'reaction',
        'adverse', 'side effect', 'dangerous', 'harmful', 'risky',
        'can i give', 'can they take', 'can use', 'is it ok'
    ]
    
    DOSAGE_KEYWORDS = [
        'how much', 'how many', 'dose', 'dosage', 'mg', 'amount',
        'give how much', 'take how much', 'right dose', 'correct dose',
        'what dose', 'what amount'
    ]
    
    DRUG_KEYWORDS = [
        'aspirin', 'ibuprofen', 'paracetamol', 'acetaminophen',
        'amoxicillin', 'penicillin', 'antibiotic', 'medicine',
        'medication', 'drug'
    ]
    
    @staticmethod
    def is_hybrid_question(question: str) -> Tuple[bool, Dict[str, bool]]:
        """
        Detect if question is asking for BOTH safety AND dosage
        
        Args:
            question: User's question
            
        Returns:
            Tuple of (is_hybrid, intent_breakdown)
                is_hybrid: True if needs multiple handlers
                intent_breakdown: {
                    'needs_safety_check': bool,
                    'needs_dosage': bool,
                    'mentioned_drug': str or None,
                    'asking_about_child': bool
                }
        """
        question_lower = question.lower()
        
        # Check for safety intent
        has_safety = any(kw in question_lower for kw in HybridQuestionDetector.SAFETY_KEYWORDS)
        
        # Check for dosage intent  
        has_dosage = any(kw in question_lower for kw in HybridQuestionDetector.DOSAGE_KEYWORDS)
        
        # Check for drug mention
        drug_mentioned = None
        for drug in HybridQuestionDetector.DRUG_KEYWORDS:
            if drug in question_lower:
                drug_mentioned = drug
                break
        
        # Check if asking about child
        asking_about_child = any(
            phrase in question_lower 
            for phrase in ['my child', 'my kid', 'child', "baby's", 'pediatric', 'kids']
        )
        
        is_hybrid = has_safety and has_dosage
        
        intent_breakdown = {
            'needs_safety_check': has_safety,
            'needs_dosage': has_dosage,
            'mentioned_drug': drug_mentioned,
            'asking_about_child': asking_about_child,
            'question_type': 'HYBRID' if is_hybrid else ('ALLERGY' if has_safety else 'MEDICATION')
        }
        
        return is_hybrid, intent_breakdown
    
    @staticmethod
    def get_handler_route(intent_breakdown: Dict[str, any]) -> List[str]:
        """
        Get list of handlers needed for this question
        
        Returns: ['ALLERGY', 'MEDICATION'] or ['ALLERGY'] or ['MEDICATION']
        """
        handlers = []
        
        if intent_breakdown['needs_safety_check']:
            handlers.append('ALLERGY')
        
        if intent_breakdown['needs_dosage']:
            handlers.append('MEDICATION')
        
        return handlers if handlers else ['GENERAL']


def demo_hybrid_detection():
    """Show how hybrid detection works"""
    
    test_questions = [
        # Hybrid questions (BOTH safety + dosage)
        "Is aspirin safe for my child? How much can I give?",
        "Can I give ibuprofen? What's the right dose?",
        "Is paracetamol safe? How much for fever?",
        "My child is allergic to penicillin. What other drugs can I give?",
        
        # Safety only
        "Is my child allergic to aspirin?",
        "Can I give ibuprofen if allergic to aspirin?",
        
        # Dosage only
        "How much ibuprofen for fever?",
        "What dose of paracetamol?",
        
        # General
        "Tell me about fever",
        "When should I call doctor?",
    ]
    
    print("=" * 80)
    print("HYBRID QUESTION DETECTION DEMO")
    print("=" * 80)
    print()
    
    for question in test_questions:
        is_hybrid, breakdown = HybridQuestionDetector.is_hybrid_question(question)
        handlers = HybridQuestionDetector.get_handler_route(breakdown)
        
        print(f"Question: {question}")
        print(f"  Type: {breakdown['question_type']}")
        print(f"  Is Hybrid: {is_hybrid}")
        print(f"  Needs Safety Check: {breakdown['needs_safety_check']}")
        print(f"  Needs Dosage: {breakdown['needs_dosage']}")
        print(f"  Drug Mentioned: {breakdown['mentioned_drug']}")
        print(f"  About Child: {breakdown['asking_about_child']}")
        print(f"  → Route to Handlers: {' + '.join(handlers)}")
        print()

if __name__ == "__main__":
    demo_hybrid_detection()
