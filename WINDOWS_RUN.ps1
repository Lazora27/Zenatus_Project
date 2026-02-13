# Zenatus Backtester - PowerShell Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      Zenatus Backtester - Local Execution Mode" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory to script location
Set-Location $PSScriptRoot

# 1. Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[INFO] Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org"
    Read-Host "Press Enter to exit"
    exit
}

# 2. Set Environment Variables
$Env:ZENATUS_CONFIG_PATH = Join-Path $PSScriptRoot "config\config.windows.yaml"
$Env:ZENATUS_BASE_PATH = $PSScriptRoot
Write-Host "[INFO] Environment variables set." -ForegroundColor Green

# 3. Create necessary directories
$dirs = @(
    "Zenatus_Dokumentation",
    "Zenatus_Dokumentation\LOG",
    "Zenatus_Dokumentation\Listing"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "[INFO] Created directory: $dir" -ForegroundColor Gray
    }
}

# 4. Install Requirements
if (Test-Path "requirements.txt") {
    Write-Host "[INFO] Installing/Checking dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt | Out-Null
} else {
    Write-Host "[WARN] requirements.txt not found." -ForegroundColor Yellow
}

# 5. Start GUI
Write-Host "[INFO] Starting GUI..." -ForegroundColor Cyan
Write-Host "If the browser doesn't open, check the URL below." -ForegroundColor Gray

try {
    # Try running module directly first as it's often more reliable with path issues
    python -m streamlit run "04_GUI\backtest_gui.py"
} catch {
    Write-Host "[WARN] python -m streamlit failed, trying direct command..." -ForegroundColor Yellow
    try {
        streamlit run "04_GUI\backtest_gui.py"
    } catch {
        Write-Host "[ERROR] Could not start Streamlit. Please ensure 'streamlit' is installed." -ForegroundColor Red
        Write-Host "Try running: pip install streamlit" -ForegroundColor Red
    }
}

Read-Host "Press Enter to close"
