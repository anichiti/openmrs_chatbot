@echo off
REM ==============================================================================
REM OpenMRS Clinical Chatbot - Automated Setup Script for Windows
REM ==============================================================================
REM This script automates the setup process for running the chatbot locally

setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║          OpenMRS Clinical Chatbot - Windows Setup Wizard                  ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download from: https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo ✓ Python is installed
python --version

REM Check if MySQL is available
mysql --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠ WARNING: MySQL client not found
    echo MySQL Server should still work if installed (just can't verify from command line)
    echo If MySQL is not installed, get it from: https://dev.mysql.com/downloads/mysql/
    echo.
) else (
    echo ✓ MySQL client is available
)

REM Check if Ollama is running
echo.
echo Checking Ollama...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -TimeoutSec 2 -ErrorAction Stop; if($r.StatusCode -eq 200) { Write-Host '✓ Ollama is running'; exit 0 } } catch { Write-Host '✗ Ollama is NOT running'; exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠ WARNING: Ollama is not running on localhost:11434
    echo You need to start Ollama before running the chatbot
    echo   1. Open Ollama application, OR
    echo   2. Run in PowerShell: ollama serve
    echo.
) else (
    echo ✓ Ollama is running
)

REM Create virtual environment if it doesn't exist
echo.
if not exist "openmrs_chatbot\venv" (
    echo Creating Python virtual environment...
    cd openmrs_chatbot
    python -m venv venv
    cd ..
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call openmrs_chatbot\venv\Scripts\activate.bat

REM Install requirements
echo.
echo Installing Python packages (this may take 2-5 minutes)...
pip install -q -r openmrs_chatbot\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)
echo ✓ All packages installed successfully

REM Test imports
echo.
echo Testing package imports...
python -c "import mysql.connector; print('  ✓ mysql.connector')" 2>nul || echo "  ✗ mysql.connector - FAILED"
python -c "import chromadb; print('  ✓ chromadb')" 2>nul || echo "  ✗ chromadb - FAILED"
python -c "import ollama; print('  ✓ ollama')" 2>nul || echo "  ✗ ollama - FAILED"
python -c "import langchain; print('  ✓ langchain')" 2>nul || echo "  ✗ langchain - FAILED"

REM Summary
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                    SETUP COMPLETE!                                        ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo NEXT STEPS:
echo.
echo 1. MAKE SURE MYSQL IS RUNNING
echo    Services → Look for "MySQL57" or "MySQL80" → Start if not running
echo.
echo 2. MAKE SURE OLLAMA IS RUNNING
echo    Open a new PowerShell and run: ollama serve
echo    Keep it running in the background
echo.
echo 3. TEST DATABASE CONNECTION
echo    Run: cd openmrs_chatbot
echo    Run: python tests/test_db_connection.py
echo.
echo 4. START THE CHATBOT
echo    Option A (Command Line):
echo       python main.py
echo.
echo    Option B (Web Interface):
echo       python app.py
echo       Then open: http://localhost:5000
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo.
pause
