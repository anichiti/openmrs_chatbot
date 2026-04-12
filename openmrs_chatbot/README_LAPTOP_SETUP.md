# OpenMRS Clinical Chatbot - Laptop Setup Guide

## Quick Summary
Your chatbot is ready for local setup! You'll need:
- ✓ MySQL database (running locally)
- ✓ Python dependencies installed
- ✓ Ollama with Llama2 (you already have this!)

---

## MANUAL SETUP STEPS (If Scripts Don't Work)

### Step 1: MySQL Database Setup

#### 1a. Install MySQL (Windows)
1. Download MySQL from: https://dev.mysql.com/downloads/mysql/
2. Run the installer
3. Choose "Server" component
4. Default port: **3306** ✓
5. Set password (we use `root` for development)

#### 1b. Start MySQL (Choose One)

**Option A - Windows Services:**
```
1. Press Win + R
2. Type: services.msc
3. Find "MySQL57" or "MySQL80"
4. Right-click → Start
```

**Option B - Command Line (PowerShell, run as Admin):**
```powershell
net start MySQL57
```

#### 1c. Create Database
```powershell
# Test connection first
mysql -u root -p

# You should see: mysql>

# Exit with: exit
```

```powershell
# Create the chatbot database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS chatbot_dev CHARACTER SET utf8 COLLATE utf8_general_ci;"
```

#### 1d. Initialize Schema (Optional - for sample data)
```powershell
# From openmrs_chatbot directory
mysql -u root -p chatbot_dev < init_database.sql
```

This creates 3 sample patients with IDs 1, 2, 3 for testing.

---

### Step 2: Verify Ollama & Llama2

#### 2a. Check if Ollama is Running
```powershell
curl http://localhost:11434/api/tags
```

You should see JSON output. If not, start Ollama:
```powershell
ollama serve
```
Keep this terminal open!

#### 2b. Verify Models
```powershell
ollama list
```

You should see:
- `llama2` ✓ (you already have this)
- `nomic-embed-text` (install if missing: `ollama pull nomic-embed-text`)

---

### Step 3: Python Setup

#### 3a. Navigate to Project
```powershell
cd c:\Users\megha\PycharmProjects\openmrs_chatbot-1\openmrs_chatbot
```

#### 3b. Create Virtual Environment
```powershell
python -m venv venv
```

#### 3c. Activate It
```powershell
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of each line.

#### 3d. Install Packages
```powershell
pip install -r requirements.txt
```

This installs:
- mysql-connector-python
- chromadb
- langchain
- ollama
- python-dotenv
- pypdf

---

### Step 4: Test Everything

#### 4a. Test Imports
```powershell
python -c "import mysql.connector; print('MySQL OK')"
python -c "import chromadb; print('ChromaDB OK')"
python -c "import ollama; print('Ollama OK')"
```

All should print `OK`.

#### 4b. Test Database Connection
```powershell
python tests/test_db_connection.py
```

You should see:
```
✓ OpenMRS database connected
✓ Query retrieved 0 records
```

---

### Step 5: Run the Chatbot

#### Option A: Command Line Interface
```powershell
python main.py
```

You'll see:
```
Initializing Clinical Chatbot...
Chatbot initialized

============================================================
CLINICAL CHATBOT - USER ROLE SELECTION
============================================================
Please select your role:
  1. Doctor
  2. Patient
============================================================

Enter your choice (1 or 2): 
```

Enter `1` for Doctor or `2` for Patient, then ask questions!

#### Option B: Web Interface (Better!)
```powershell
python app.py
```

Then open: http://localhost:5000

You'll see a nice chat interface where you can:
- Select role
- Chat with the chatbot
- View patient information
- Ask about medications, immunizations, vitals

---

## .env File Configuration

Your `.env` file is already set up with:
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=chatbot_dev
DB_USER=root
DB_PASSWORD=root
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBED_MODEL=nomic-embed-text
```

### If you changed the MySQL password:
Edit `.env` and change:
```
DB_PASSWORD=youractualpassword
```

---

## Troubleshooting

### "Database connection failed"
1. Is MySQL running? (Check services.msc)
2. Correct password in .env?
3. Can you run: `mysql -u root -p` ?

### "Ollama connection refused"
1. Is Ollama running? (`ollama serve`)
2. Keep that terminal window open
3. Test: `curl http://localhost:11434/api/tags`

### "Module not found" errors
1. Virtual environment activated? `(venv)` in prompt?
2. Reinstall: `pip install -r requirements.txt`
3. Check specific package: `pip install mysql-connector-python==8.2.0`

### "Port 5000 already in use"
Edit `app.py` line and change port:
```python
if __name__ == '__main__':
    app.run(port=5001)  # Change to 5001 or another port
```

Then access: http://localhost:5001

### Still stuck?
Run the verification script:
```powershell
python troubleshooting/verify_config.py
```

This will check all components and tell you what's missing.

---

## Day-to-Day Usage

### Every time you start:

**Terminal 1 - Start Ollama:**
```powershell
ollama serve
```
Keep this running!

**Terminal 2 - Run Chatbot:**
```powershell
cd openmrs_chatbot
.\venv\Scripts\Activate.ps1
python app.py  # or python main.py for CLI
```

Then open: http://localhost:5000

---

## Windows Batch Scripts to Help

I've created some automation scripts for you:

### setup.bat
Run once for initial setup:
```bash
setup.bat
```

### quickstart.ps1
Run before each session:
```powershell
.\quickstart.ps1
```

Then just run: `python app.py`

### init_db.ps1
Initialize the database (one time):
```powershell
cd openmrs_chatbot
.\init_db.ps1
```

---

## Understanding the Project Structure

```
openmrs_chatbot/
├── app.py                    # Flask web server
├── main.py                   # CLI chatbot
├── requirements.txt          # Python packages
├── .env                      # Your configuration (created)
├── init_database.sql         # Database schema
│
├── agents/                   # AI agents for different tasks
│   ├── triage_agent.py       # Identify user type & intent
│   ├── sql_agent.py          # Query the database
│   ├── knowledge_agent.py    # Search knowledge base
│   └── ... (more agents)
│
├── database/
│   └── db.py                 # MySQL connection & queries
│
├── utils/
│   ├── config.py             # Configuration loader
│   └── logger.py             # Logging setup
│
├── data/                     # JSON data files
│   ├── medication.json
│   └── immunization.json
│
├── static/                   # CSS and JavaScript (for web UI)
├── templates/                # HTML templates
├── knowledge_base/           # Your PDF documents go here
└── tests/                    # Test scripts
```

---

## What the Chatbot Can Do

### For Doctors:
- Look up patient records
- Get medication recommendations
- Check immunization schedules
- Review vital signs
- Calculate medical metrics

### For Patients:
- View simplified health information
- Ask about medications
- Learn about health milestones
- Get patient-friendly explanations

---

## Next Steps After Setup

1. ✅ Database running
2. ✅ Python packages installed
3. ✅ Ollama with llama2 ready
4. ▶ Add PDF documents to `knowledge_base/doctor/` and `knowledge_base/patient/`
5. ▶ Run: `python technical/init_kb.py` to index PDFs
6. ▶ Start using the chatbot!

---

## Still Need Help?

Check the full documentation:
- [Full Setup Guide](./SETUP_GUIDE.txt)
- `troubleshooting/verify_config.py` - Auto diagnostic tool
- `docs/COMPLETION_SUMMARY.txt` - Project overview

Or contact support if any step doesn't work for you.

---

**Good luck with your chatbot setup! 🚀**
