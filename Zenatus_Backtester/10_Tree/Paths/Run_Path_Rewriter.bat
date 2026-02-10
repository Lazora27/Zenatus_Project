@echo off
setlocal

set VENV_PY="/opt/Zenatus_Backtester\Zenatus_Backtest_venv\Scripts\python.exe"
set SCRIPT="/opt/Zenatus_Backtester\10_Tree\Paths\path_rewriter.py"

%VENV_PY% %SCRIPT%

endlocal
