@echo off
REM Drug Dosage Handler - Quick Setup Script
REM Downloads required Ollama models

echo.
echo ======================================================================
echo  Drug Dosage Handler - Installing Required Models
echo ======================================================================
echo.

echo [STEP 1/2] Pulling embedding model (nomic-embed-text)...
echo Note: This may take 5-10 minutes depending on your internet speed
echo.
ollama pull nomic-embed-text

if errorlevel 1 (
    echo.
    echo ERROR: Failed to pull nomic-embed-text
    echo Make sure Ollama is running: ollama serve
    pause
    exit /b 1
)

echo.
echo [STEP 2/2] Pulling language model (llama2)...
echo Note: llama2 is large (~4GB), this may take 10-20 minutes
echo.
ollama pull llama2

if errorlevel 1 (
    echo.
    echo ERROR: Failed to pull llama2
    echo You can continue without this for testing, but it's recommended
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo  Setup Complete!
echo ======================================================================
echo.
echo Next steps:
echo  1. Initialize knowledge base: python technical\init_kb.py
echo  2. Verify setup: python verify_drug_dosage_setup.py
echo  3. Run chatbot: python main.py
echo.
pause
