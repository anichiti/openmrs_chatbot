"""
AUTOMATED INTENT CLASSIFIER EVALUATION & TRAINING FEEDBACK

This module provides:
1. Automated performance metrics (accuracy, precision, recall)
2. Detailed classification analysis
3. Training feedback for improving the classifier
4. Keyword effectiveness analysis
5. Confusion matrix generation

Success Criteria (MUST ACHIEVE):
- Overall accuracy: 95%
- MCP trigger accuracy: 100%
- No multi-intent misclassifications
- All keywords properly detected
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.triage_agent import TriageAgent, INTENT_KEYWORDS
from utils.logger import setup_logger
from collections import defaultdict

logger = setup_logger(__name__)

class ClassifierEvaluator:
    """Evaluates intent classifier performance with detailed analytics"""
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.results = []
        self.confusion_matrix = defaultdict(lambda: defaultdict(int))
        self.intent_stats = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0})
        self.keyword_effectiveness = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    def evaluate_classification(self, question, expected_intent, expected_agent):
        """Evaluate a single classification and track metrics"""
        result = self.triage_agent.triage(question)
        actual_intent = result.get('intent')
        actual_agent = result.get('agent')
        
        # Check if classification is correct
        intent_correct = actual_intent == expected_intent
        agent_correct = actual_agent == expected_agent
        overall_correct = intent_correct and agent_correct
        
        # Track for confusion matrix
        self.confusion_matrix[expected_intent][actual_intent] += 1
        
        # Track metrics for each intent
        if overall_correct:
            self.intent_stats[expected_intent]['tp'] += 1
        else:
            # False positive for actual intent, false negative for expected
            self.intent_stats[expected_intent]['fn'] += 1
            self.intent_stats[actual_intent]['fp'] += 1
        
        # Analyze keywords that were matched (skip for GENERAL_MEDICAL_QUERY)
        if expected_intent in INTENT_KEYWORDS:
            question_lower = question.lower()
            for keyword in INTENT_KEYWORDS[expected_intent]['keywords']:
                self.keyword_effectiveness[keyword]['total'] += 1
                if keyword in question_lower and intent_correct:
                    self.keyword_effectiveness[keyword]['correct'] += 1
        
        self.results.append({
            'question': question,
            'expected_intent': expected_intent,
            'expected_agent': expected_agent,
            'actual_intent': actual_intent,
            'actual_agent': actual_agent,
            'correct': overall_correct,
            'intent_correct': intent_correct,
            'agent_correct': agent_correct
        })
        
        return {
            'correct': overall_correct,
            'intent_correct': intent_correct,
            'agent_correct': agent_correct
        }
    
    def calculate_metrics(self):
        """Calculate precision, recall, and F1 for each intent"""
        metrics = {}
        # Include all intents that appear in results, not just INTENT_KEYWORDS
        all_intents = set()
        for result in self.results:
            all_intents.add(result['expected_intent'])
            all_intents.add(result['actual_intent'])
        
        for intent in all_intents:
            tp = self.intent_stats[intent]['tp']
            fp = self.intent_stats[intent]['fp']
            fn = self.intent_stats[intent]['fn']
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics[intent] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'tp': tp,
                'fp': fp,
                'fn': fn
            }
        
        return metrics
    
    def print_detailed_report(self):
        """Print comprehensive evaluation report"""
        total_tests = len(self.results)
        correct_tests = sum(1 for r in self.results if r['correct'])
        accuracy = (correct_tests / total_tests * 100) if total_tests > 0 else 0
        
        # MCP trigger accuracy
        mcp_correct = sum(1 for r in self.results if r['agent_correct'])
        mcp_accuracy = (mcp_correct / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("INTENT CLASSIFIER EVALUATION REPORT")
        print("="*80)
        print(f"Total Classifications: {total_tests}")
        print(f"Correct Classifications: {correct_tests}")
        print(f"Overall Accuracy: {accuracy:.1f}%")
        print(f"MCP Agent Trigger Accuracy: {mcp_accuracy:.1f}%")
        print(f"\nStatus: {'CHECK PASSED (95%)' if accuracy >= 95 else 'FAIL FAILED (<95%)'}")
        print(f"MCP Status: {'CHECK PERFECT (100%)' if mcp_accuracy == 100 else 'FAIL IMPERFECT'}")
        
        # Per-intent metrics
        print("\n" + "="*80)
        print("PER-INTENT METRICS")
        print("="*80)
        
        metrics = self.calculate_metrics()
        for intent, metric in metrics.items():
            print(f"\n{intent}:")
            print(f"  Precision: {metric['precision']*100:.1f}%")
            print(f"  Recall:    {metric['recall']*100:.1f}%")
            print(f"  F1-Score:  {metric['f1']*100:.1f}%")
            print(f"  TP: {metric['tp']}, FP: {metric['fp']}, FN: {metric['fn']}")
        
        # Confusion matrix
        self.print_confusion_matrix()
        
        # Keyword effectiveness
        self.print_keyword_analysis()
        
        # Failed classifications
        self.print_failures()
    
    def print_confusion_matrix(self):
        """Print confusion matrix of classifications"""
        print("\n" + "="*80)
        print("CONFUSION MATRIX (Expected vs Actual)")
        print("="*80)
        
        intents = list(INTENT_KEYWORDS.keys())
        
        # Header
        print("\nExpected \\ Actual | " + " | ".join(f"{intent[:15]:<15}" for intent in intents))
        print("-" * (50 + len(intents) * 20))
        
        # Matrix
        for expected in intents:
            row = f"{expected[:15]:<15} | "
            for actual in intents:
                count = self.confusion_matrix[expected][actual]
                row += f"{count:>15} | "
            print(row)
    
    def print_keyword_analysis(self):
        """Analyze keyword effectiveness in classification"""
        print("\n" + "="*80)
        print("KEYWORD EFFECTIVENESS ANALYSIS")
        print("="*80)
        
        # Sort keywords by effectiveness (highest first)
        sorted_keywords = sorted(
            self.keyword_effectiveness.items(),
            key=lambda x: (x[1]['correct'] / x[1]['total'] if x[1]['total'] > 0 else 0),
            reverse=True
        )
        
        print(f"\n{'Keyword':<25} {'Correct':<10} {'Total':<10} {'Accuracy':<10} {'Status':<10}")
        print("-" * 65)
        
        for keyword, stats in sorted_keywords:
            total = stats['total']
            correct = stats['correct']
            acc = (correct / total * 100) if total > 0 else 0
            status = "CHECK Good" if acc >= 80 else "[WARNING] Weak" if acc >= 60 else "FAIL Poor"
            
            print(f"{keyword:<25} {correct:<10} {total:<10} {acc:<9.1f}% {status:<10}")
        
        # Recommendations
        print("\n" + "-"*65)
        print("RECOMMENDATIONS:")
        weak_keywords = [kw for kw, stats in sorted_keywords 
                        if stats['total'] > 0 and (stats['correct']/stats['total']*100) < 80]
        
        if weak_keywords:
            print(f"[WARNING] Consider improving these weak keywords:")
            for kw in weak_keywords[:5]:
                print(f"  - {kw}")
        else:
            print("CHECK All keywords are performing well!")
    
    def print_failures(self):
        """Print detailed analysis of failed classifications"""
        failures = [r for r in self.results if not r['correct']]
        
        if not failures:
            print("\n" + "="*80)
            print("CHECK NO FAILURES - ALL CLASSIFICATIONS CORRECT!")
            print("="*80)
            return
        
        print("\n" + "="*80)
        print(f"FAILED CLASSIFICATIONS ({len(failures)} failures)")
        print("="*80)
        
        for i, failure in enumerate(failures[:10], 1):  # Show first 10 failures
            print(f"\nFailure #{i}:")
            print(f"  Question: {failure['question']}")
            print(f"  Expected: {failure['expected_intent']} -> {failure['expected_agent']}")
            print(f"  Got:      {failure['actual_intent']} -> {failure['actual_agent']}")
            
            if not failure['intent_correct']:
                print(f"  FAIL Intent misclassified")
            if not failure['agent_correct']:
                print(f"  FAIL Agent misrouted")
        
        if len(failures) > 10:
            print(f"\n... and {len(failures) - 10} more failures")


def run_comprehensive_evaluation():
    """Run comprehensive evaluation on all test cases"""
    evaluator = ClassifierEvaluator()
    
    # All test cases with expected intents and agents
    test_cases = [
        # Medication queries
        ("What is the dose of paracetamol for a 2 year old?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Side effects of ibuprofen?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Can amoxicillin cause rash?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("Maximum dosage of acetaminophen?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("What is ibuprofen used for?", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        
        # Immunization queries
        ("When should MMR vaccine be given?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("What vaccines are given at birth?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Polio vaccine schedule?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Is BCG given at birth?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Which vaccines at 6 months?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        
        # Milestone queries
        ("When should baby start walking?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When do babies start talking?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When should baby sit without support?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("When should baby crawl?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        ("Normal age for smiling?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        
        # Patient record queries
        ("Show patient 101 lab results", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Blood pressure of patient 200", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Medical history of patient 300", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Vitals of patient 400", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        ("Diagnosis of patient 123", "PATIENT_RECORD_QUERY", "SQL_AGENT"),
        
        # Multi-intent (priority test)
        ("Patient 101 paracetamol dose", "MEDICATION_QUERY", "MCP_MEDICATION_AGENT"),
        ("When should patient 101 get MMR vaccine?", "IMMUNIZATION_QUERY", "MCP_IMMUNIZATION_AGENT"),
        ("Is patient 200 walking normally?", "MILESTONE_QUERY", "MCP_MILESTONE_AGENT"),
        
        # General queries (no specific MCP)
        ("Hello", "GENERAL_MEDICAL_QUERY", None),
        ("How are you?", "GENERAL_MEDICAL_QUERY", None),
        ("What is fever?", "GENERAL_MEDICAL_QUERY", None),
    ]
    
    # Run evaluations
    for question, expected_intent, expected_agent in test_cases:
        evaluator.evaluate_classification(question, expected_intent, expected_agent)
    
    # Print report
    evaluator.print_detailed_report()
    
    # Return success/failure
    total = len(evaluator.results)
    correct = sum(1 for r in evaluator.results if r['correct'])
    accuracy = (correct / total * 100) if total > 0 else 0
    
    return 0 if accuracy >= 95 else 1


def main():
    """Main evaluation entry point"""
    print("\n")
    print("[" + "="*78 + "]")
    print("|" + " AUTOMATED CLASSIFIER EVALUATION & TRAINING FEEDBACK ".center(78) + "|")
    print("|" + " Performance Analysis & Improvement Recommendations ".center(78) + "|")
    print("[" + "="*78 + "]")
    
    exit_code = run_comprehensive_evaluation()
    
    print("\n" + "="*80)
    print("EVALUATION COMPLETE")
    print("="*80)
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
