# ==============================================================================
# OpenMRS Clinical Chatbot - Database Initialization Script
# ==============================================================================
# Creates the chatbot database and initializes tables

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              Database Initialization Script                               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get credentials
Write-Host "MySQL Credentials Required" -ForegroundColor Yellow
$dbUser = Read-Host "Enter MySQL username (default: root)"
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "root" }

$dbPass = Read-Host "Enter MySQL password (press Enter if none)" -AsSecureString
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($dbPass))

$dbHost = Read-Host "Enter MySQL host (default: localhost)"
if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = "localhost" }

Write-Host ""
Write-Host "[1/3] Testing MySQL connection..." -ForegroundColor Yellow

# Test connection
$testCmd = "SELECT 1"
try {
    if ($password) {
        $result = mysql -h $dbHost -u $dbUser -p$password -e $testCmd 2>&1
    } else {
        $result = mysql -h $dbHost -u $dbUser -e $testCmd 2>&1
    }
    Write-Host "✓ MySQL connection successful" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to connect to MySQL" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "[2/3] Creating database..." -ForegroundColor Yellow

# Create database
$createDbCmd = "CREATE DATABASE IF NOT EXISTS chatbot_dev CHARACTER SET utf8 COLLATE utf8_general_ci;"
try {
    if ($password) {
        mysql -h $dbHost -u $dbUser -p$password -e $createDbCmd
    } else {
        mysql -h $dbHost -u $dbUser -e $createDbCmd
    }
    Write-Host "✓ Database created successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create database" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "[3/3] Initializing database schema..." -ForegroundColor Yellow

# Initialize schema
try {
    $sqlFile = Join-Path (Get-Location) "init_database.sql"
    if (Test-Path $sqlFile) {
        if ($password) {
            Get-Content $sqlFile | mysql -h $dbHost -u $dbUser -p$password chatbot_dev
        } else {
            Get-Content $sqlFile | mysql -h $dbHost -u $dbUser chatbot_dev
        }
        Write-Host "✓ Database schema initialized" -ForegroundColor Green
    } else {
        Write-Host "✗ init_database.sql not found" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Failed to initialize schema" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "DATABASE INITIALIZATION COMPLETE!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database Details:" -ForegroundColor Yellow
Write-Host "  Host: $dbHost"
Write-Host "  User: $dbUser"
Write-Host "  Database: chatbot_dev"
Write-Host ""
Write-Host "Sample data inserted:"
Write-Host "  • 3 Patient records"
Write-Host "  • Patient IDs: 1, 2, 3"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Update .env file if you used different credentials"
Write-Host "  2. Test connection: python tests/test_db_connection.py"
Write-Host "  3. Run chatbot: python main.py"
Write-Host ""
