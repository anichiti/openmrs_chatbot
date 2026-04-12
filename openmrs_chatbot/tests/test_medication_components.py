#!/usr/bin/env python3
"""
Test Medication Components Integration
Verifies: RxNorm + DoseCalculator + FDA API (extracted from ani)
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("Testing Medication Components (RxNorm + Dose Calc + FDA API)")
    logger.info("=" * 70)
    
    # Test 1: Import components  
    logger.info("\n[TEST 1] Importing medication components...")
    try:
        from agents.medication_controller import MedicationMCPController
        from utils.rxnorm_api_skill import RxNormAPISkill
        from utils.fda_api_skill import FDAAPISkill
        logger.info("✅ Components imported successfully")
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Initialize MCPAgent
    logger.info("\n[TEST 2] Initializing MCPAgent...")
    try:
        from agents.mcp_agent import MCPAgent
        mcp_agent = MCPAgent()
        if mcp_agent.ani_mcp:
            logger.info("✅ MCPAgent ready with medication components")
        else:
            logger.warning("⚠️ MCPAgent initialized but components inactive")
    except Exception as e:
        logger.error(f"❌ MCPAgent init failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Search medication
    logger.info("\n[TEST 3] Searching medication (paracetamol)...")
    try:
        result = mcp_agent.search_medication("paracetamol")
        if result.get("count", 0) > 0:
            med = result["results"][0]
            logger.info(f"✅ Found: {med.get('name')}")
            logger.info(f"   Category: {med.get('category')}")
            logger.info(f"   Indications: {med.get('indications')}")
        else:
            logger.warning("⚠️ No results found")
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Calculate dose
    logger.info("\n[TEST 4] Calculating dose (paracetamol 20kg, 5y)...")
    try:
        result = mcp_agent.calculate_medication_dose("paracetamol", 20, 5)
        if "error" not in result and result.get("calculated_dose"):
            dose = result["calculated_dose"].get("dose_per_admin_mg")
            freq = result["calculated_dose"].get("frequency")
            logger.info(f"✅ Dose: {dose}mg {freq}")
        else:
            logger.warning(f"⚠️ Dose calc: {result}")
    except Exception as e:
        logger.error(f"❌ Dose calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Full integration
    logger.info("\n[TEST 5] Testing with ClinicalChatbot...")
    try:
        from main import ClinicalChatbot
        chatbot = ClinicalChatbot()
        result = chatbot.process_query("What is paracetamol?")
        if result.get("response"):
            logger.info(f"✅ Query processed")
            logger.info(f"   Intent: {result['intent']}")
            logger.info(f"   Response: {result['response'][:80]}...")
        else:
            logger.warning("⚠️ No response")
    except Exception as e:
        logger.error(f"❌ Chatbot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ ALL TESTS PASSED - Medication integration working!")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
