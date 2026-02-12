#!/usr/bin/env bash
set -euo pipefail

cd /opt/Zenatus_Backtester
source Zenatus_Backtest_venv/bin/activate

python -u 02_Agents/pipeline_orchestrator.py
