# -*- coding: utf-8 -*-
import sys
import json
import time
import csv
import os
import argparse
import concurrent.futures
import pandas as pd
import numpy as np
import importlib.util
from pathlib import Path
from datetime import datetime

# CONFIG
BASE_PATH = Path(os.environ.get("ZENATUS_BASE_PATH", r"/opt/Zenatus_Backtester"))
INDICATORS_PATH = BASE_PATH / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys"
DATA_PATH = BASE_PATH / "99_Historic_Data" / "Forex" / "Major"
SPREADS_PATH = BASE_PATH / "00_Backtester" / "Spreads"
PARAM_OPT_PATH = BASE_PATH / "01_Strategy" / "Parameter_Optimization"
DOC_BASE = Path(r"/opt/Zenatus_Dokumentation")

# Output Paths
RESULTS_DIR = DOC_BASE / "Dokumentation" / "Fixed_Exit" / "1h"
QUEUE_FILE = DOC_BASE / "Listing" / "Full_backtest" / "1h" / "indicators_working.json"

# Settings
TIMEFRAME = "1h"
FREQ = "1H"
SYMBOLS = ["EUR_USD", "GBP_USD", "USD_CHF", "USD_CAD", "AUD_USD", "NZD_USD"]
DATE_START = "2023-01-01"
DATE_END = datetime.now().strftime("%Y-%m-%d")
INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
SLIPPAGE_PIPS = 0.5  # Base slippage, might be adjusted per symbol if needed
COMMISSION_PER_LOT = 3.0
PIP_VALUE = 0.0001
TIMEOUT_SEC = 1800  # 30m

try:
    import vectorbt as vbt
except:
    print("[FATAL] vectorbt not installed")
    sys.exit(1)

def load_data():
    spreads_df = pd.read_csv(SPREADS_PATH / "FTMO_SPREADS_FOREX.csv")
    spreads = {row["Symbol"].replace("/", "_"): row["Typical_Spread_Pips"] for _, row in spreads_df.iterrows()}
    cache = {}
    for symbol in SYMBOLS:
        fp = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
        if not fp.exists():
            print(f"[WARN] {symbol} data not found at {fp}")
            continue
        df = pd.read_csv(fp)
        df.columns = [c.lower() for c in df.columns]
        
        # Handle duplicate columns
        if len(df.columns) != len(set(df.columns)):
            print(f"[WARN] Duplicate columns in {symbol}: {df.columns.tolist()}")
            # Keep first occurrence
            df = df.loc[:, ~df.columns.duplicated()]
            
        if "time" not in df.columns and "Time" in [c for c in df.columns]:
            df.rename(columns={"Time": "time"}, inplace=True)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
        cache[symbol] = {"full": df}
        print(f"[DATA] {symbol} bars={len(df)}")
    return spreads, cache

def get_combo_limit(ind_num):
    # Logic: Ind 1-2 = 3500, Ind 3-4 = 5000, Ind 5+ = 10000
    if ind_num <= 2:
        return 3500
    elif ind_num <= 4:
        return 5000
    else:
        return 10000

def generate_combos(ind_num, limit):
    handbook_file = PARAM_OPT_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
    tp_sl = []
    
    if handbook_file.exists():
        try:
            with open(handbook_file, "r", encoding="utf-8") as f:
                hb = json.load(f)
            
            entry = None
            if isinstance(hb, list):
                for item in hb:
                    if str(item.get("Indicator_Num")) == str(ind_num):
                        entry = item
                        break
            elif isinstance(hb, dict):
                entry = hb.get(str(ind_num))
                
            if entry:
                exit_params = entry.get("Exit_Params", entry)
                tp_values = exit_params.get("tp_pips", {}).get("values", [])
                sl_values = exit_params.get("sl_pips", {}).get("values", [])
                
                # Check if values are actually lists
                if not isinstance(tp_values, list): tp_values = []
                if not isinstance(sl_values, list): sl_values = []
                
                for tp in tp_values:
                    for sl in sl_values:
                        if tp > sl:
                            tp_sl.append((tp, sl))
        except Exception as e:
            print(f"[WARN] Handbook error: {e}")

    # STRICT MODE: No Fallbacks allowed as per user instruction.
    # Only combinations explicitly defined in the Handbook will be used.
    
    # Limit logic
    if len(tp_sl) > limit:
        # Simple slicing
        return tp_sl[:limit]
    
    return tp_sl

def calculate_metrics(pf, spread_pips, tp_pips, sl_pips):
    trades = pf.trades.count()
    if trades < 1:
        return None
    
    total_profit = pf.total_profit()
    lot_size = POSITION_SIZE / 100000
    total_commission = trades * COMMISSION_PER_LOT * lot_size
    net_profit = total_profit - total_commission
    net_return = (net_profit / INITIAL_CAPITAL) * 100
    
    equity = pf.value()
    cummax = equity.expanding().max()
    drawdowns = (equity - cummax) / cummax
    max_dd = abs(drawdowns.min()) * 100
    
    win_rate = pf.trades.win_rate() * 100
    pfactor = pf.trades.profit_factor()
    sharpe = pf.sharpe_ratio()
    
    # New metrics requested
    winning_trades = pf.trades.winning.count()
    losing_trades = pf.trades.losing.count()
    avg_win = pf.trades.winning.pnl.mean()
    avg_loss = pf.trades.losing.pnl.mean()
    highest_win = pf.trades.winning.pnl.max()
    highest_loss = pf.trades.losing.pnl.min()
    gross_profit = pf.trades.winning.pnl.sum() # approx
    
    vals = {
        "TP_Pips": tp_pips,
        "SL_Pips": sl_pips,
        "Spread_Pips": spread_pips,
        "Slippage_Pips": SLIPPAGE_PIPS,
        "Entry_period": "NA", # TODO: If we have entry params, we should log them. For now NA or derived.
        "Total_Return": float(f"{net_return:.4f}"),
        "Max_Drawdown": float(f"{max_dd:.4f}"),
        "Daily_Drawdown": 0.0, # Placeholder, calculation complex
        "Win_Rate_%": float(f"{win_rate:.2f}"),
        "Total_Trades": int(trades),
        "Winning_Trades": int(winning_trades),
        "Losing_Trades": int(losing_trades),
        "Avg_Win": float(f"{avg_win:.2f}") if not np.isnan(avg_win) else 0.0,
        "Avg_Loss": float(f"{avg_loss:.2f}") if not np.isnan(avg_loss) else 0.0,
        "Highest_Win": float(f"{highest_win:.2f}") if not np.isnan(highest_win) else 0.0,
        "Highest_Loss": float(f"{highest_loss:.2f}") if not np.isnan(highest_loss) else 0.0,
        "Gross_Profit": float(f"{gross_profit:.2f}"),
        "Commission": float(f"{total_commission:.2f}"),
        "Net_Profit": float(f"{net_profit:.2f}"),
        "Profit_Factor": float(f"{0.0 if np.isnan(pfactor) or np.isinf(pfactor) else pfactor:.3f}"),
        "Sharpe_Ratio": float(f"{0.0 if np.isnan(sharpe) or np.isinf(sharpe) else sharpe:.3f}"),
    }
    return vals

def batch_backtest(df, entries, tp_sl_combos, spread_pips):
    tp_array = []
    sl_array = []
    valid = []
    for tp_pips, sl_pips in tp_sl_combos:
        effective_tp = (tp_pips - spread_pips - SLIPPAGE_PIPS) * PIP_VALUE
        effective_sl = (sl_pips + spread_pips + SLIPPAGE_PIPS) * PIP_VALUE
        if effective_tp > 0 and effective_sl > 0:
            tp_array.append(effective_tp)
            sl_array.append(effective_sl)
            valid.append((tp_pips, sl_pips))
            
    if not valid: return []
    
    # VectorBT Execution
    # Note: For 10000 combos, doing all at once might be memory intensive.
    # Splitting into chunks of 1000 might be safer.
    
    CHUNK_SIZE = 1000
    all_results = []
    
    for i in range(0, len(valid), CHUNK_SIZE):
        chunk_valid = valid[i:i+CHUNK_SIZE]
        chunk_tp = np.array(tp_array[i:i+CHUNK_SIZE])
        chunk_sl = np.array(sl_array[i:i+CHUNK_SIZE])
        
        # Always use DataFrame to ensure consistent 2D shape for vbt
        close_in = pd.concat([df["close"]]*len(chunk_valid), axis=1)
        entries_in = pd.concat([entries]*len(chunk_valid), axis=1)
        
        # Ensure unique column names
        cols = [f"c{k}" for k in range(len(chunk_valid))]
        close_in.columns = cols
        entries_in.columns = cols
        
        try:
            pf = vbt.Portfolio.from_signals(
                close=close_in,
                entries=entries_in,
                exits=False,
                tp_stop=chunk_tp,
                sl_stop=chunk_sl,
                init_cash=INITIAL_CAPITAL,
                size=POSITION_SIZE,
                size_type="amount",
                fees=0.0,
                freq=FREQ
            )
            
            # Batch calculate metrics (much faster and avoids indexing issues)
            # All these return Series of shape (N,)
            m_trades = pf.trades.count()
            m_total_profit = pf.total_profit()
            
            # Equity & Drawdown
            equity = pf.value()
            cummax = equity.expanding().max()
            drawdowns = (equity - cummax) / cummax
            m_max_dd = abs(drawdowns.min()) * 100
            
            m_win_rate = pf.trades.win_rate() * 100
            m_pfactor = pf.trades.profit_factor()
            m_sharpe = pf.sharpe_ratio()
            
            m_winning_trades = pf.trades.winning.count()
            m_losing_trades = pf.trades.losing.count()
            m_avg_win = pf.trades.winning.pnl.mean()
            m_avg_loss = pf.trades.losing.pnl.mean()
            m_highest_win = pf.trades.winning.pnl.max()
            m_highest_loss = pf.trades.losing.pnl.min()
            m_gross_profit = pf.trades.winning.pnl.sum()

            lot_size = POSITION_SIZE / 100000

            for idx, (tp_pips, sl_pips) in enumerate(chunk_valid):
                trades = int(m_trades.iloc[idx])
                if trades < 1: continue

                total_profit = m_total_profit.iloc[idx]
                total_commission = trades * COMMISSION_PER_LOT * lot_size
                net_profit = total_profit - total_commission
                net_return = (net_profit / INITIAL_CAPITAL) * 100
                
                max_dd = float(m_max_dd.iloc[idx])
                win_rate = float(m_win_rate.iloc[idx])
                pfactor = float(m_pfactor.iloc[idx])
                sharpe = float(m_sharpe.iloc[idx])
                
                winning_trades = int(m_winning_trades.iloc[idx])
                losing_trades = int(m_losing_trades.iloc[idx])
                avg_win = float(m_avg_win.iloc[idx])
                avg_loss = float(m_avg_loss.iloc[idx])
                highest_win = float(m_highest_win.iloc[idx])
                highest_loss = float(m_highest_loss.iloc[idx])
                gross_profit = float(m_gross_profit.iloc[idx])

                vals = {
                    "TP_Pips": tp_pips,
                    "SL_Pips": sl_pips,
                    "Spread_Pips": spread_pips,
                    "Slippage_Pips": SLIPPAGE_PIPS,
                    "Entry_period": "NA",
                    "Total_Return": float(f"{net_return:.4f}"),
                    "Max_Drawdown": float(f"{max_dd:.4f}"),
                    "Daily_Drawdown": 0.0,
                    "Win_Rate_%": float(f"{win_rate:.2f}"),
                    "Total_Trades": int(trades),
                    "Winning_Trades": int(winning_trades),
                    "Losing_Trades": int(losing_trades),
                    "Avg_Win": float(f"{avg_win:.2f}") if not np.isnan(avg_win) else 0.0,
                    "Avg_Loss": float(f"{avg_loss:.2f}") if not np.isnan(avg_loss) else 0.0,
                    "Highest_Win": float(f"{highest_win:.2f}") if not np.isnan(highest_win) else 0.0,
                    "Highest_Loss": float(f"{highest_loss:.2f}") if not np.isnan(highest_loss) else 0.0,
                    "Gross_Profit": float(f"{gross_profit:.2f}"),
                    "Commission": float(f"{total_commission:.2f}"),
                    "Net_Profit": float(f"{net_profit:.2f}"),
                    "Profit_Factor": float(f"{0.0 if np.isnan(pfactor) or np.isinf(pfactor) else pfactor:.3f}"),
                    "Sharpe_Ratio": float(f"{0.0 if np.isnan(sharpe) or np.isinf(sharpe) else sharpe:.3f}"),
                }
                all_results.append(vals)

        except Exception as e:
            print(f"[ERR-BATCH] {len(chunk_valid)} combos: {e}")
            import traceback
            traceback.print_exc()
                
    return all_results

def process_indicator(ind_name, spreads, data_cache):
    try:
        ind_num = int(ind_name.split("_")[0])
    except:
        return f"[SKIP] Invalid name {ind_name}"
        
    limit = get_combo_limit(ind_num)
    combos = generate_combos(ind_num, limit)
    
    # Find Script
    ind_path = None
    for f in INDICATORS_PATH.glob(f"{ind_name}*.py"):
        if f.stem == ind_name:
            ind_path = f
            break
    if not ind_path:
        return f"[SKIP] File not found {ind_name}"
        
    # Load Class
    spec = importlib.util.spec_from_file_location(ind_name, ind_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    klass = None
    for attr in dir(module):
        obj = getattr(module, attr)
        if isinstance(obj, type) and ("Indicator" in attr or hasattr(obj, "generate_signals_fixed")):
            klass = obj
            break
    if not klass:
        return f"[SKIP] Class not found {ind_name}"
        
    # Run
    all_rows = []
    start_time = time.time()
    
    for symbol in SYMBOLS:
        if symbol not in data_cache: continue
        df = data_cache[symbol]["full"]
        spread_pips = spreads.get(symbol, 2.0)
        
        try:
            instance = klass()
            signals = instance.generate_signals_fixed(df, {})
            entries = signals["entries"].values
            if isinstance(entries, np.ndarray):
                entries = pd.Series(entries, index=df.index)
            entries = entries.fillna(False).astype(bool)
            
            if entries.sum() > 0:
                res = batch_backtest(df, entries, combos, spread_pips)
                for r in res:
                    row = {"Indicator_Num": ind_num, "Indicator": ind_name, "Symbol": symbol, "Timeframe": TIMEFRAME}
                    row.update(r)
                    all_rows.append(row)
        except Exception as e:
            print(f"[ERR] {ind_name} {symbol}: {e}")
            import traceback
            traceback.print_exc()
            
    # Save
    if all_rows:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / f"{ind_num:03d}_{ind_name}_{TIMEFRAME}.csv"
        
        # Reorder columns as requested
        cols = ["Indicator_Num","Indicator","Symbol","Timeframe","TP_Pips","SL_Pips","Spread_Pips","Slippage_Pips",
                "Entry_period","Total_Return","Max_Drawdown","Daily_Drawdown","Win_Rate_%","Total_Trades",
                "Winning_Trades","Losing_Trades","Avg_Win","Avg_Loss","Highest_Win","Highest_Loss",
                "Gross_Profit","Commission","Net_Profit","Profit_Factor","Sharpe_Ratio"]
        
        df_out = pd.DataFrame(all_rows)
        # Add missing columns with 0/NA
        for c in cols:
            if c not in df_out.columns:
                df_out[c] = 0
        
        df_out[cols].to_csv(csv_path, index=False, float_format="%.6f")
        return f"[DONE] {ind_name} saved with {len(all_rows)} rows. ({int(time.time()-start_time)}s)"
    else:
        return f"[DONE] {ind_name} produced no results."

def main():
    print("=== FULL BACKTEST STARTED ===")
    
    # Load Queue
    if not QUEUE_FILE.exists():
        print("No working queue found.")
        return
        
    with open(QUEUE_FILE, "r") as f:
        data = json.load(f)
        queue = data.get("scripts", [])
        
    if not queue:
        print("Queue is empty.")
        return
        
    spreads, data_cache = load_data()
    
    # Parallel Execution
    max_workers = os.cpu_count() or 4
    print(f"Processing {len(queue)} indicators with {max_workers} workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_indicator, ind, spreads, data_cache): ind for ind in queue}
        
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            print(res)

if __name__ == "__main__":
    main()
