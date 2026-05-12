# OpenMRS Clinical Chatbot

A sophisticated AI-powered clinical chatbot built with Flask, integrating with OpenMRS healthcare systems to provide intelligent medical query responses, drug information lookup, and clinical decision support.

## 🌟 Features

### Core Capabilities
- **Multi-Role Support**: Separate response formatting for doctors and patients
- **Intent Classification**: Two-layer intent recognition (keyword-based + embedding-based with LLM fallback)
- **Clinical Data Integration**: Direct integration with OpenMRS database for patient records
- **Drug Information Management**: Comprehensive drug dosage, interactions, and FDA approval status lookup
- **Allergy Management**: Patient allergy history tracking and contraindication checking
- **Immunization Tracking**: Immunization history and milestone tracking
- **Vital Signs Monitoring**: Patient vital signs management and response formatting

### Advanced Features
- **Dual-Layer Intent Classification System**: Keyword matching + Sentence transformers + LLM-based fallback
- **Knowledge Base Integration**: Vector database (ChromaDB) for semantic search over medical knowledge
- **LLM Hallucination Prevention**: Strategic gating ensures LLM is only used for safe operations
- **Database-Driven Responses**: Prioritizes structured data over generative responses for critical queries
- **Validation Agent**: Multi-layer validation to prevent dangerous medical misinformation
- **Workflow Tracing**: Comprehensive logging for debugging and auditing chat interactions

### Query Types Supported
- **Medication Queries**: Drug information, dosage calculations, side effects
- **Allergy Queries**: Patient allergy screening and contraindication checking
- **Immunization Queries**: Vaccination records and milestone tracking
- **Vital Signs**: Blood pressure, temperature, heart rate monitoring
- **General Medical Questions**: Knowledge-based responses with citation support

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Flask Web Application                        │
│                   (Doctor & Patient Interfaces)                   │
└────────────────────────┬─────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌────────┐    ┌────────────┐   ┌──────────┐
    │  Chat  │    │  Triage    │   │ Workflow │
    │  API   │    │  Agent     │   │  Tracer  │
    └────┬───┘    └───┬────────┘   └──────────┘
         │            │
         └────────┬───┘
                  ▼
        ┌──────────────────────┐
        │  Intent Classifier   │
        │  (2-Layer System)     │
        └──┬────────────────┬───┘
           │                │
      ┌────▼──────┐    ┌───▼──────┐
      │  Keywords │    │ Embeddings│
      │  Matching │    │ + LLM     │
      └───────────┘    └───────────┘
           │
    ┌──────┴──────────────────────────────┐
    │    Task-Specific Agent Routing       │
    └──────┬──────────────────────────────┘
           │
   ┌───────┼────────────┬────────────┬──────────┐
   ▼       ▼            ▼            ▼          ▼
┌──────┐┌────────┐┌──────────┐┌─────────┐┌───────────┐
│ SQL  ││Drug    ││Allergy   ││Immunization│Validation│
│Agent ││Handler ││Fetcher   ││Fetcher   ││Agent     │
└────┬─┘└──┬─────┘└────┬─────┘└────┬─────┘└──┬───────┘
     │     │          │            │         │
     └─────┼──────────┼────────────┼─────────┘
           │          │            │
           ▼          ▼            ▼
      ┌────────────────────────────────┐
      │  OpenMRS Database + Knowledge  │
      │         Vector Store           │
      └────────────────────────────────┘
           │         │          │
           ▼         ▼          ▼
      ┌─────────────────────────────────┐
      │  Response Agents (Doctor/Patient)│
      └─────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **TwoLayerIntentClassifier** | Intent recognition using keywords + embeddings |
| **SQLAgent** | Database queries for patient records |
| **DrugDosageHandler** | Medication-related query routing & dosage calculations |
| **AllergyOpenMRSFetcher** | Allergy history retrieval from OpenMRS |
| **ImmunizationOpenMRSFetcher** | Vaccination record management |
| **ValidationAgent** | Safety validation to prevent harmful recommendations |
| **MCPAgent** | Model Context Protocol integration |
| **KnowledgeAgent** | Vector database queries for medical knowledge |
| **ResponseAgent** | Role-specific response formatting |

## 📋 Prerequisites

- **Python 3.8+** (Python 3.10+ recommended)
- **MySQL 5.7+** (or MySQL 8.0)
- **Ollama** with Llama 2 model
- **Windows 10+** (or Linux/macOS with modifications)

### System Requirements
- 8GB RAM minimum (16GB recommended for optimal performance)
- 10GB disk space for models and database
- Internet connection for initial setup

## 🚀 Installation & Setup

### Step 1: Prerequisites Setup

#### Install MySQL
```powershell
# Download from: https://dev.mysql.com/downloads/mysql/
# Or use package manager (Windows):
choco install mysql

# Verify installation
mysql --version
```

#### Install Ollama with Llama 2
```powershell
# Download from: https://ollama.ai
# Or install via package manager:
choco install ollama

# Pull Llama 2 model
ollama pull llama2

# Start Ollama service (if not running)
ollama serve
```

### Step 2: Clone and Setup Repository

```powershell
# Clone the repository
git clone https://github.com/yourusername/openmrs_chatbot.git
cd openmrs_chatbot

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r openmrs_chatbot/requirements.txt
```

### Step 3: Database Setup

```powershell
# Create database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS chatbot_dev CHARACTER SET utf8 COLLATE utf8_general_ci;"

# Initialize database schema
cd openmrs_chatbot
python init_db.ps1
```

Or use the provided batch files:
```powershell
.\setup.bat              # Complete setup
.\openmrs_chatbot\init_db.ps1   # Database initialization only
```

### Step 4: Configuration

Create `.env` file in `openmrs_chatbot/` directory:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=chatbot_dev
FLASK_ENV=development
FLASK_DEBUG=True
```

### Step 5: Run Application

```powershell
# Make sure Ollama is running in another terminal
ollama serve

# In another terminal, activate venv and run:
cd openmrs_chatbot
python app.py

# Access web interface at http://localhost:5000
```

## 📖 Usage

### Web Interface

1. **Navigate to** `http://localhost:5000`
2. **Select role**: Doctor or Patient
3. **Enter patient ID** (if available in database)
4. **Ask clinical questions**:
   - "What is the recommended dosage of amoxicillin for a 5-year-old?"
   - "Show me patient allergies"
   - "What are the side effects of metformin?"
   - "Check immunization status"

### API Endpoints

#### Chat Endpoint
```
POST /api/chat
Content-Type: application/json

{
    "user_input": "What medication can I take for headache?",
    "user_role": "patient",  // or "doctor"
    "patient_id": "12345"    // optional
}

Response:
{
    "response": "For headaches, you can use...",
    "intent": "MEDICATION_QUERY",
    "confidence": 0.95,
    "trace_id": "abc123"
}
```

#### Patient Lookup
```
GET /api/patients?name=John&limit=10

Response:
{
    "patients": [
        {
            "patient_id": "12345",
            "name": "John Doe",
            "age": "35y 2m",
            "gender": "M"
        }
    ]
}
```

#### Trace Lookup (Debug)
```
GET /api/trace/<trace_id>

Response:
{
    "trace_id": "abc123",
    "user_input": "What is paracetamol?",
    "intent": "MEDICATION_QUERY",
    "agents_used": ["DrugDosageHandler", "ValidationAgent"],
    "timestamp": "2024-05-12T10:30:00Z",
    "response": "Paracetamol (acetaminophen) is..."
}
```

## 📁 Project Structure

```
openmrs_chatbot/
├── agents/                      # AI agents for different tasks
│   ├── triage_agent.py          # Patient triage and priority
│   ├── two_layer_classifier.py  # Intent classification (keywords + embeddings)
│   ├── sql_agent.py             # Database query agent
│   ├── drug_dosage_handler.py   # Drug information & dosage
│   ├── allergy_openmrs_fetcher.py
│   ├── immunization_openmrs_fetcher.py
│   ├── validation_agent.py      # Safety validation
│   ├── mcp_agent.py             # Model Context Protocol
│   ├── knowledge_agent.py       # Vector DB queries
│   ├── response_agent.py        # Response formatting
│   └── ...
├── database/
│   ├── db.py                    # OpenMRS database connection
│   └── __init__.py
├── utils/
│   ├── config.py                # Configuration & constants
│   ├── logger.py                # Logging setup
│   ├── dose_calculator.py       # Pediatric dosage calculations
│   ├── warning_engine.py        # Drug interaction warnings
│   ├── workflow_tracer.py       # Request tracing for debugging
│   └── ...
├── vectorstore/
│   ├── chroma.py                # ChromaDB integration
│   └── chroma_data/             # Vector store data
├── data/
│   ├── drug_knowledge_base.json # Drug information
│   ├── immunization.json        # Immunization data
│   ├── milestones.json          # Clinical milestones
│   └── ...
├── static/
│   ├── css/style.css
│   ├── js/chat.js
│   └── ...
├── templates/
│   ├── index.html               # Doctor interface
│   ├── chat.html                # Chat interface
│   └── ...
├── technical/
│   ├── docker-compose.yml       # Docker setup (optional)
│   ├── Dockerfile
│   └── ...
├── app.py                       # Flask web application
├── main.py                      # ClinicalChatbot main class
├── requirements.txt             # Python dependencies
└── init_db.ps1                  # Database initialization script
```

## 🤖 Intent Classification System

The chatbot uses a sophisticated 2-layer intent classification system:

### Layer 1: Keyword Matching
- Fast, deterministic classification
- ~40 intent categories with keyword mappings
- Covers 80%+ of queries

### Layer 2: Embedding-Based + LLM Fallback
- Used when Layer 1 confidence < 0.75
- Sentence transformers for semantic similarity
- LLM fallback for ambiguous cases
- Requires Ollama + Llama 2 model

### Supported Intents
- `MEDICATION_QUERY` - Drug info, dosage, side effects
- `ALLERGY_CHECK` - Allergy screening
- `IMMUNIZATION_QUERY` - Vaccination records
- `VITAL_SIGNS_QUERY` - Patient vitals
- `GENERAL_MEDICAL_QUERY` - Knowledge-based questions
- `PATIENT_LOOKUP` - Find patient records
- `TRIAGE_QUERY` - Patient urgency assessment
- `DRUG_INTERACTION_CHECK` - Medication interactions
- And more...

## 🔒 Safety & Validation

The system implements multiple layers of validation:

1. **Intent Validation**: Ensures only appropriate intents trigger actions
2. **Data Validation**: Validates patient IDs and drug information
3. **Response Validation**: Checks responses for harmful content
4. **LLM Gating**: Restricts LLM use to safe operations (formatting, fallback)
5. **Database Primacy**: Prefers verified database data over LLM outputs

## 📊 Knowledge Base

The system maintains multiple knowledge sources:

- **Drug Database**: Dosage, interactions, side effects, FDA status
- **Patient Records**: OpenMRS database (medications, allergies, vitals)
- **Clinical Knowledge**: Vector database with medical documents (ChromaDB)
- **Immunization Data**: Vaccination schedules and milestones
- **Warning Database**: Known drug interactions and contraindications

## 🔍 Debugging & Tracing

Enable workflow tracing for debugging:

```powershell
# View trace for a specific request
GET /api/trace/<trace_id>

# View all recent traces
GET /api/traces?limit=10

# Clear traces
POST /api/traces/clear
```

Example trace shows:
- User input and intent classification
- Agents invoked and their outputs
- Database queries executed
- Final response generation

## 🛠️ Development

### Running Tests
```powershell
# (Tests to be added)
pytest tests/
```

### Code Style
- Follow PEP 8 conventions
- Use type hints where possible
- Document complex functions

### Adding New Intents
1. Add keywords to `INTENT_KEYWORDS` in `triage_agent.py`
2. Create handling agent if needed
3. Add response formatter in `response_agent.py`
4. Update validation rules in `validation_agent.py`

### Adding Drug Information
1. Update `data/drug_knowledge_base.json`
2. Update ChromaDB vector store
3. Re-index for semantic search

## 📚 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flask | 3.0.0 | Web framework |
| mysql-connector-python | 8.2.0 | MySQL database |
| chromadb | 0.4.14 | Vector database |
| langchain | 0.0.352 | LLM chains |
| ollama | 0.1.9 | Ollama integration |
| sentence-transformers | 2.2.2 | Embeddings |
| python-dotenv | 1.0.0 | Configuration |

## 🚢 Deployment

### Docker Deployment
```powershell
# Build image
docker-compose -f openmrs_chatbot/technical/docker-compose.yml build

# Run containers
docker-compose up -d

# Access at http://localhost:5000
```

### Production Deployment
- Use a production WSGI server (Gunicorn)
- Configure reverse proxy (Nginx)
- Use environment-specific config
- Enable HTTPS/SSL
- Set up proper database backups
- Configure monitoring and logging

## 📝 Configuration

### Environment Variables
```
OLLAMA_HOST         - Ollama server URL (default: http://localhost:11434)
OLLAMA_MODEL        - LLM model name (default: llama2)
MYSQL_HOST          - Database host (default: localhost)
MYSQL_USER          - Database user
MYSQL_PASSWORD      - Database password
MYSQL_DATABASE      - Database name
FLASK_ENV          - Environment (development/production)
FLASK_DEBUG        - Enable debug mode (True/False)
LOG_LEVEL          - Logging level (DEBUG/INFO/WARNING/ERROR)
```

## 🐛 Troubleshooting

### Ollama Connection Error
```
Error: Failed to connect to Ollama at http://localhost:11434

Solution:
1. Ensure Ollama is running: ollama serve
2. Check if port 11434 is not blocked
3. Update OLLAMA_HOST in .env if using different port
```

### MySQL Connection Error
```
Error: MySQL connection failed

Solution:
1. Verify MySQL is running: net start MySQL57
2. Check credentials in .env
3. Ensure database exists: CREATE DATABASE chatbot_dev;
```

### Llama 2 Model Not Found
```
Error: Model llama2 not found

Solution:
1. Pull the model: ollama pull llama2
2. Wait for download to complete (~5GB)
3. Verify: ollama list
```

### Slow Response Times
- Increase available RAM (model requires ~4GB)
- Check GPU availability for acceleration
- Reduce ChromaDB query scope
- Enable caching for frequent queries

## 📖 Additional Documentation

- [SETUP_GUIDE.txt](SETUP_GUIDE.txt) - Detailed installation instructions
- [KNOWLEDGE_BASE_INTEGRATION_METHODS.md](KNOWLEDGE_BASE_INTEGRATION_METHODS.md) - Architecture details
- [WORKFLOW_TRACE_GUIDE.txt](WORKFLOW_TRACE_GUIDE.txt) - Debugging guide
- [docs/ALLERGY_WORKFLOW.md](openmrs_chatbot/docs/ALLERGY_WORKFLOW.md) - Allergy workflow

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows PEP 8 style guide
- All functions have docstrings
- Changes don't break existing tests
- New features include tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

**This is a research/educational project.** The chatbot is designed to assist healthcare professionals and should not replace professional medical advice. Always consult qualified healthcare providers for medical decisions.

## 👥 Authors

- [Your Name/Team] - Initial development

## 🙏 Acknowledgments

- OpenMRS community and documentation
- Ollama and Llama 2 team
- ChromaDB for vector database technology
- Flask community

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review workflow traces for debugging

---

**Last Updated**: May 12, 2026  
**Version**: 1.0.0  
**Status**: Active Development
