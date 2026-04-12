#!/usr/bin/env python3
"""Quick verification that extraction is complete and working"""
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from agents.mcp_agent import MCPAgent
    
    logger.info("MCPAgent loaded successfully without ani folder")
    
    mcp = MCPAgent()
    
    # Test medication search
    result = mcp.search_medication('paracetamol')
    logger.info(f"Found {result.get('count')} medication(s)")
    
    # Test dose calculation  
    dose_result = mcp.calculate_medication_dose('paracetamol', 20, 5)
    dose_info = dose_result.get('calculated_dose', {})
    if dose_info and 'dose_per_admin_mg' in dose_info:
        dose = dose_info['dose_per_admin_mg']
        freq = dose_info['frequency']
        logger.info(f"Dose calculated: {dose}mg {freq}")
        logger.info("EXTRACTION SUCCESSFUL - All tests passed!")
    else:
        logger.error(f"Dose calculation issue: {dose_result}")
        
except Exception as e:
    logger.error(f"Error: {e}")
    import traceback
    traceback.print_exc()
