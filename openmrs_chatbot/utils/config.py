import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration (MySQL via Docker)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3308"))
DB_NAME = os.getenv("DB_NAME", "chatbot-dev")
DB_USER = os.getenv("DB_USER", "openmrs")
DB_PASSWORD = os.getenv("DB_PASSWORD", "openmrs")
DB_TYPE = os.getenv("DB_TYPE", "mysql")

# Ollama Configuration (Local LLM) - Free & No API limits!
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
DOCTOR_KB_DIR = os.path.join(KNOWLEDGE_BASE_DIR, "doctor")
PATIENT_KB_DIR = os.path.join(KNOWLEDGE_BASE_DIR, "patient")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore", "chroma_data")
RESPONSES_FILE = os.path.join(BASE_DIR, "responses.json")

# MCP Database Files
MEDICATION_DB = os.path.join(DATA_DIR, "medication.json")
IMMUNIZATION_DB = os.path.join(DATA_DIR, "immunization.json")
MILESTONE_DB = os.path.join(DATA_DIR, "milestones.json")

# Safety Configuration
ENABLE_SAFETY_LAYER = True
CONFIDENCE_THRESHOLD = 0.7

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(BASE_DIR, "chatbot.log")
