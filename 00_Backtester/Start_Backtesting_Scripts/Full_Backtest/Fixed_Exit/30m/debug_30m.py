# -*- coding: utf-8 -*-
import sys
import json
import time
import pandas as pd
import numpy as np
import importlib.util
from pathlib import Path
from datetime import datetime
import itertools

# CONFIG
BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys"
DATA_PATH = BASE_PATH / "99_Historic_Data" / "Forex" / "Major"
PARAM_OPT_PATH = BASE_PATH / "01_Strategy" / "Parameter_Optimization"
TIMEFRAME = "30m"
SYMBOLS = ["EUR_USD"] # Test just one
DATE_START = "2023-01-01"
DATE_END = datetime.now().strftime("%Y-%m-%d")

def load_handbook_entry(ind_num):
    handbook_file = PARAM_OPT_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
    print(f"Loading handbook from: {handbook_file}")
    if not handbook_file.exists():
        print("Handbook file not found!")
        return None
    
    try:
        with open(handbook_file, "r", encoding="utf-8") as f:
            hb = json.load(f)
        
        if isinstance(hb, list):
            for item in hb:
                if str(item.get("Indicator_Num")) == str(ind_num):
                    return item
        elif isinstance(hb, dict):
            return hb.get(str(ind_num))
    except Exception as e:
        print(f"[WARN] Handbook error: {e}")
    return None

def generate_param_grids(ind_num):
    entry = load_handbook_entry(ind_num)
    if not entry:
        print(f"No entry found for {ind_num}")
        return [], []
        
    # 1. Parse Entry Params
    entry_params_config = entry.get("Entry_Params", {})
    entry_keys = list(entry_params_config.keys())
    entry_value_lists = []
    
    for k in entry_keys:
        cfg = entry_params_config[k]
        vals = cfg.get("values", [])
        if not isinstance(vals, list): vals = []
        entry_value_lists.append(vals)
        
    # Cartesian product for Entry Params
    entry_combos = []
    if entry_value_lists:
        for combo in itertools.product(*entry_value_lists):
            param_dict = dict(zip(entry_keys, combo))
            entry_combos.append(param_dict)
    else:
        entry_combos = [{}]

    # 2. Parse Exit Params (TP/SL)
    exit_params = entry.get("Exit_Params", {})
    tp_values = exit_params.get("tp_pips", {}).get("values", [])
    sl_values = exit_params.get("sl_pips", {}).get("values", [])
    
    if not isinstance(tp_values, list): tp_values = []
    if not isinstance(sl_values, list): sl_values = []
    
    exit_combos = []
    for tp in tp_values:
        for sl in sl_values:
            if tp > sl:
                exit_combos.append((tp, sl))
                
    return entry_combos, exit_combos

def debug_indicator(ind_name):
    print(f"Debugging {ind_name}...")
    try:
        ind_num = int(ind_name.split("_")[0])
    except:
        print("Invalid name format")
        return

    entry_combos, exit_combos = generate_param_grids(ind_num)
    print(f"Entry Combos: {len(entry_combos)}")
    print(f"Exit Combos: {len(exit_combos)}")
    
    if not entry_combos: print("No entry combos!")
    if not exit_combos: print("No exit combos!")
    
    # Find Script
    ind_path = None
    print(f"Searching in {INDICATORS_PATH}")
    for f in INDICATORS_PATH.glob(f"{ind_name}*.py"):
        if f.stem == ind_name:
            ind_path = f
            break
    
    if not ind_path:
        print(f"File not found: {ind_name}")
        return
    print(f"Found script: {ind_path}")
    
    # Load Class
    spec = importlib.util.spec_from_file_location(ind_name, ind_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    klass = None
    for attr in dir(module):
        obj = getattr(module, attr)
        if isinstance(obj, type) and ("Indicator" in attr or hasattr(obj, "generate_signals_fixed")):
            klass = obj
            print(f"Found class: {attr}")
            break
    
    if not klass:
        print("Class not found!")
        return
        
    # Load Data
    symbol = SYMBOLS[0]
    fp = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
    print(f"Loading data from {fp}")
    if not fp.exists():
        print("Data file not found!")
        return
        
    df = pd.read_csv(fp)
    df.columns = [c.lower() for c in df.columns]
    if "time" not in df.columns and "Time" in [c for c in df.columns]:
        df.rename(columns={"Time": "time"}, inplace=True)
    df["time"] = pd.to_datetime(df["time"])
    df.set_index("time", inplace=True)
    df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
    print(f"Data loaded: {len(df)} rows")
    
    # Run one combo
    if entry_combos:
        params = entry_combos[0]
        print(f"Running with params: {params}")
        instance = klass()
        try:
            signals = instance.generate_signals_fixed(df, params)
            print("Signals generated.")
            print(signals.head())
        except Exception as e:
            print(f"Error generating signals: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_indicator("004_trend_dema")
