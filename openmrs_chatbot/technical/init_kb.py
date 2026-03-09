#!/usr/bin/env python3

"""
Initialize the knowledge base by indexing PDF documents.
Run this after adding PDF files to knowledge_base/doctor/ and knowledge_base/patient/
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vectorstore.chroma import VectorStore
from utils.logger import setup_logger

logger = setup_logger(__name__)


def initialize_knowledge_base():
    logger.info("Starting knowledge base initialization...")
    
    vectorstore = VectorStore()
    
    logger.info("Indexing doctor knowledge base...")
    if vectorstore.index_doctor_kb():
        logger.info("Doctor knowledge base indexed successfully")
    else:
        logger.warning("Doctor knowledge base indexing completed with warnings")
    
    logger.info("Indexing patient knowledge base...")
    if vectorstore.index_patient_kb():
        logger.info("Patient knowledge base indexed successfully")
    else:
        logger.warning("Patient knowledge base indexing completed with warnings")
    
    logger.info("Knowledge base initialization complete")
    print("\n" + "=" * 60)
    print("Knowledge Base Initialization Complete")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review logs in chatbot.log for any warnings")
    print("2. Run: python main.py")
    print("=" * 60)


if __name__ == "__main__":
    initialize_knowledge_base()
