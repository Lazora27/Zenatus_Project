# -*- coding: utf-8 -*-
"""
VectorBT Backtest - 1H Timeframe
Pfad-Header vorbereitet für konsistente Nutzung im Backtester
"""

from pathlib import Path

# ============================================================================
# CONFIGURATION (Pfad-Header)
# ============================================================================

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
SPREADS_PATH = BASE_PATH / "12_Spreads"

TIMEFRAME = "1h"
FREQ = "1H"

if __name__ == "__main__":
    print(f"[INIT] VECTORBT_1H_BACKTEST paths ready: {INDICATORS_PATH}")
