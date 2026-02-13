@echo off
TITLE Zenatus Backtester Machine
CLS

ECHO ========================================================
ECHO       Zenatus Backtester - Local Execution Mode
ECHO ========================================================
ECHO.

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

:: 3. Install Requirements
ECHO [INFO] Checking dependencies...
pip install -r requirements.txt >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [WARN] Could not install requirements automatically.
    ECHO Please run: pip install -r requirements.txt
)

:: 4. Start GUI
ECHO [INFO] Starting GUI...
ECHO.
ECHO Access the GUI in your browser if it doesn't open automatically.
ECHO.

streamlit run Zenatus_Backtester\04_GUI\backtest_gui.py

PAUSE
