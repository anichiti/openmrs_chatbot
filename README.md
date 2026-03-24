# OpenMRS Clinical Chatbot

An intelligent, agent-based clinical decision-support chatbot for OpenMRS.  
It routes natural-language questions from doctors, patients, and parents to
specialised agents (medication, allergy, immunisation, vitals, patient records,
hybrid) and returns role-aware, safety-validated responses.

---

## Quick-start

### 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.9+ | Tested with 3.9 – 3.12 |
| [Ollama](https://ollama.ai/download) | Local LLM server — install and keep it running (`ollama serve`) |
| MySQL 5.7 / 8.x | Or use the provided Docker Compose file |

### 2. Clone & enter the project

```bash
git clone https://github.com/anichiti/openmrs_chatbot.git
cd openmrs_chatbot
```

### 3. Create and activate a virtual environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r openmrs_chatbot/requirements.txt
```

> **This is the most common cause of the `ModuleNotFoundError: No module named 'ollama'`
> error.** Running `main.py` before installing requirements will fail at the very
> first import.

### 5. Pull required Ollama models

Make sure Ollama is running (`ollama serve` in a separate terminal), then:

```bash
# Windows — run the provided helper script
openmrs_chatbot\setup_ollama_models.bat

# macOS / Linux
ollama pull llama2
ollama pull nomic-embed-text
```

### 6. Set up the database

**Option A — Docker (recommended)**

```bash
cd openmrs_chatbot/technical
docker compose up -d
```

**Option B — existing MySQL instance**

Create a `.env` file in the `openmrs_chatbot/` directory (copy from the example
below) and point it at your MySQL server:

```dotenv
DB_HOST=localhost
DB_PORT=3308
DB_NAME=chatbot-dev
DB_USER=openmrs
DB_PASSWORD=openmrs
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBED_MODEL=nomic-embed-text
```

Restore the OpenMRS SQL dump:

```bash
cd openmrs_chatbot
python troubleshooting/restore_openmrs.py
```

### 7. Initialise the knowledge base & vector store

```bash
cd openmrs_chatbot
python technical/init_kb.py
```

### 8. Verify the configuration

```bash
cd openmrs_chatbot
python troubleshooting/verify_config.py
```

### 9. Run the chatbot

```bash
cd openmrs_chatbot   # must run from this directory
python main.py
```

---

## Project layout

```
openmrs_chatbot/          ← run all commands from here
├── main.py               ← entry point
├── requirements.txt      ← Python dependencies
├── setup_ollama_models.bat
├── agents/               ← triage, medication, allergy, immunisation, …
├── data/                 ← JSON knowledge bases (medication, immunisation, milestones)
├── database/             ← MySQL connector
├── knowledge_base/       ← raw PDF & text sources
├── technical/            ← Docker Compose, schema helpers, KB initialiser
├── troubleshooting/      ← verify_config.py, restore_openmrs.py
├── utils/                ← config, logger
└── vectorstore/          ← ChromaDB vector store (generated)
docs/
└── flowcharts/           ← architecture diagrams (PNG + generator script)
```

---

## Architecture flowcharts

High-resolution architecture diagrams are in [`docs/flowcharts/`](docs/flowcharts/README.md).

| Flowchart | Description |
|---|---|
| [`flowchart1_agent_architecture.png`](docs/flowcharts/flowchart1_agent_architecture.png) | Full multi-agent pipeline |
| [`flowchart2_knowledge_classification.png`](docs/flowcharts/flowchart2_knowledge_classification.png) | Knowledge classification & routing |
| [`flowchart3_architecture_flow.png`](docs/flowcharts/flowchart3_architecture_flow.png) | Architecture, flow & safety logic |

To regenerate the PNGs:

```bash
pip install matplotlib pillow
python docs/flowcharts/generate_flowcharts.py
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'ollama'` | Run `pip install -r openmrs_chatbot/requirements.txt` |
| `ModuleNotFoundError: No module named 'agents'` | Run `python main.py` **from inside** the `openmrs_chatbot/` directory |
| `ConnectionRefusedError` (Ollama) | Start Ollama: `ollama serve` |
| `mysql.connector.errors.DatabaseError` | Check DB is running and `.env` credentials are correct |
| Models not found | Run `ollama pull llama2 && ollama pull nomic-embed-text` |
