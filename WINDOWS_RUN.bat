@echo off
TITLE Zenatus Backtester Machine
CLS

ECHO ========================================================
ECHO       Zenatus Backtester - Local Execution Mode
ECHO ========================================================
ECHO.

:: Ensure we are in the script's directory
CD /D "%~dp0"

:: 1. Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python is not installed or not in PATH.
    ECHO Please install Python 3.10+ from python.org
    PAUSE
    EXIT /B
)

:: 2. Set Environment Variables
SET ZENATUS_CONFIG_PATH=%~dp0config\config.windows.yaml
SET ZENATUS_BASE_PATH=%~dp0

:: 3. Create necessary directories
IF NOT EXIST "Zenatus_Dokumentation" MKDIR "Zenatus_Dokumentation"
IF NOT EXIST "Zenatus_Dokumentation\LOG" MKDIR "Zenatus_Dokumentation\LOG"
IF NOT EXIST "Zenatus_Dokumentation\Listing" MKDIR "Zenatus_Dokumentation\Listing"

:: 4. Install Requirements
ECHO [INFO] Checking dependencies...
IF EXIST "requirements.txt" (
    pip install -r requirements.txt >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [WARN] Could not install requirements automatically.
        ECHO Please run: pip install -r requirements.txt
    )
) ELSE (
    ECHO [WARN] requirements.txt not found in %CD%
)

:: 5. Start GUI
ECHO [INFO] Starting GUI...
ECHO.
ECHO Access the GUI in your browser if it doesn't open automatically.
ECHO.

:: Try direct run
streamlit run 04_GUI\backtest_gui.py

IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO [WARN] 'streamlit' command failed. Trying 'python -m streamlit'...
    python -m streamlit run 04_GUI\backtest_gui.py
)

PAUSE
