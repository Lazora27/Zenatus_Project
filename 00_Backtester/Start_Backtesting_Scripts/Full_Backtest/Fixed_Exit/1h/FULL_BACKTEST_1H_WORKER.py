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

# Settings (Defaults)
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

# Output Paths
RESULTS_DIR = DOC_BASE / "Dokumentation" / "Fixed_Exit" / TIMEFRAME
RUN_ID = "Default"

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

import itertools

def get_combo_limit(ind_num):
    # Logic: Ind 1-2 = 3500, Ind 3-4 = 5000, Ind 5+ = 10000
    if ind_num <= 2:
        return 3500
    elif ind_num <= 4:
        return 5000
    else:
        return 10000

def load_handbook_entry(ind_num):
    handbook_file = PARAM_OPT_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
    if not handbook_file.exists():
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
            # Create dict {param_name: value}
            param_dict = dict(zip(entry_keys, combo))
            entry_combos.append(param_dict)
    else:
        # If no entry params (unlikely, but possible), use empty dict
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

def calculate_metrics(pf, spread_pips, tp_pips, sl_pips, entry_params):
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
        "Entry_period": "NA", # Deprecated, see Parameter columns
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
    # Splitting into smaller chunks reduces RAM-Spitzenlast.
    
    CHUNK_SIZE = 100
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

import multiprocessing

def worker_process(ind_name, spreads, data_cache, queue):
    """
    Function to run in a separate process.
    """
    try:
        # Re-import needed modules here to be safe in multiprocessing context
        import pandas as pd
        import numpy as np
        import importlib.util
        import vectorbt as vbt # Ensure vbt is available
        
        # We need to reconstruct the process_indicator logic here
        # Or better, just call the logic function if we split it.
        # But for minimal changes, let's just copy the logic or import it?
        # Since this script IS the module, we can just use the function logic.
        
        # NOTE: Passing 'data_cache' (large dict of DFs) to a process might be slow due to pickling.
        # However, since we use 'fork' on Linux, it should be copy-on-write and fast.
        
        res = run_indicator_logic(ind_name, spreads, data_cache)
        queue.put(res)
    except Exception as e:
        queue.put(f"[FATAL-WORKER] {e}")

def run_indicator_logic(ind_name, spreads, data_cache):
    # This is the actual calculation logic extracted from process_indicator
    try:
        try:
            ind_num = int(ind_name.split("_")[0])
        except:
            return f"[SKIP] Invalid name {ind_name}"
            
        limit = get_combo_limit(ind_num)
        entry_combos, exit_combos = generate_param_grids(ind_num)
        
        if not entry_combos or not exit_combos:
            return f"[SKIP] No combos found in Handbook for {ind_name}"
    
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
        
        # Global limit counter for this indicator
        total_tests_run = 0
        
        for symbol in SYMBOLS:
            if symbol not in data_cache: continue
            df = data_cache[symbol]["full"]
            spread_pips = spreads.get(symbol, 2.0)
            
            symbol_tests_run = 0
            
            try:
                # Iterate through Entry Params
                for entry_params in entry_combos:
                    if symbol_tests_run >= limit:
                        break
                        
                    remaining = limit - symbol_tests_run
                    if remaining <= 0: break
                    
                    current_exit_combos = exit_combos
                    if len(current_exit_combos) > remaining:
                        current_exit_combos = current_exit_combos[:remaining]
                    
                    instance = klass()
                    
                    try:
                        signals = instance.generate_signals_fixed(df, entry_params)
                    except TypeError:
                        for k, v in entry_params.items():
                            setattr(instance, k, v)
                        signals = instance.generate_signals_fixed(df, {})
                    
                    entries = signals["entries"].values
                    if isinstance(entries, np.ndarray):
                        entries = pd.Series(entries, index=df.index)
                    entries = entries.fillna(False).astype(bool)
                    
                    if entries.sum() > 0:
                        res = batch_backtest(df, entries, current_exit_combos, spread_pips)
                        
                        for r in res:
                            row = {"Indicator_Num": ind_num, "Indicator": ind_name, "Symbol": symbol, "Timeframe": TIMEFRAME}
                            row.update(r)
                            
                            p_idx = 1
                            for p_name, p_val in entry_params.items():
                                if p_idx <= 10:
                                    row[f"Parameter {p_idx}"] = p_val
                                p_idx += 1
                            
                            all_rows.append(row)
                            
                        symbol_tests_run += len(res)
                    else:
                        symbol_tests_run += len(current_exit_combos)
    
            except Exception as e:
                print(f"[ERR] {ind_name} {symbol}: {e}")
                
        # Save
        if all_rows:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            csv_path = RESULTS_DIR / f"{ind_num:03d}_{ind_name}_{TIMEFRAME}.csv"
            
            param_cols = [f"Parameter {i}" for i in range(1, 11)]
            
            cols = ["Indicator_Num","Indicator","Symbol","Timeframe"] + param_cols + \
                   ["TP_Pips","SL_Pips","Spread_Pips","Slippage_Pips",
                    "Entry_period","Total_Return","Max_Drawdown","Daily_Drawdown","Win_Rate_%","Total_Trades",
                    "Winning_Trades","Losing_Trades","Avg_Win","Avg_Loss","Highest_Win","Highest_Loss",
                    "Gross_Profit","Commission","Net_Profit","Profit_Factor","Sharpe_Ratio"]
            
            df_out = pd.DataFrame(all_rows)
            for c in cols:
                if c not in df_out.columns:
                    if "Parameter" in c:
                        df_out[c] = "NA"
                    else:
                        df_out[c] = 0
            
            df_out[cols].to_csv(csv_path, index=False, float_format="%.6f")
            
            best_row = df_out.loc[df_out["Net_Profit"].idxmax()]
            duration = time.time() - start_time
            
            now_str = datetime.now().strftime("%H:%M:%S")
            duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
            
            summary = (f"[{now_str}] [{ind_num:03d}] [{ind_name}] [{TIMEFRAME}] "
                       f"[Combos: {len(df_out)}] "
                       f"[Ret: {best_row['Total_Return']}%] "
                       f"[DD: {best_row['Max_Drawdown']}%] "
                       f"[PF: {best_row['Profit_Factor']}] "
                       f"[Sharpe: {best_row['Sharpe_Ratio']}] "
                       f"[Trades: {best_row['Total_Trades']}] "
                       f"[WR: {best_row['Win_Rate_%']}%] "
                       f"[{duration_str}]")
            
            return summary
        else:
            return f"[{datetime.now().strftime('%H:%M:%S')}] [{ind_num:03d}] [{ind_name}] NO RESULTS ({int(time.time()-start_time)}s)"
            
    except Exception as e:
        return f"[FATAL] {ind_name} crashed: {e}"

def process_indicator(ind_name, spreads, data_cache):
    # Wrapper that uses multiprocessing to enforce HARD TIMEOUT
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=worker_process, args=(ind_name, spreads, data_cache, q))
    p.start()
    p.join(timeout=TIMEOUT_SEC)
    
    if p.is_alive():
        p.terminate()
        # Give it a second
        time.sleep(1)
        if p.is_alive():
            p.kill() # Hard kill (SIGKILL)
        print(f"[TIMEOUT] {ind_name} killed after {TIMEOUT_SEC}s")
        return f"[TIMEOUT] {ind_name} killed"
    
    if not q.empty():
        return q.get()
    else:
        return f"[ERR] {ind_name} process finished but returned no result"

def main():
    global TIMEFRAME, FREQ, SYMBOLS, DATE_START, DATE_END, INITIAL_CAPITAL, RESULTS_DIR, RUN_ID
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts", type=str, help="Comma-separated list of scripts to process")
    parser.add_argument("--worker-id", type=int, default=0, help="ID of this worker node")
    
    # GUI Support
    parser.add_argument("--timeframe", type=str, help="Timeframe (e.g. 1h, 5m)")
    parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols")
    parser.add_argument("--start-date", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--capital", type=float, help="Initial capital")
    parser.add_argument("--run-id", type=str, help="Unique Run ID for output folder")
    
    args = parser.parse_args()

    print(f"=== WORKER {args.worker_id} STARTED ===")
    
    # Apply Overrides
    if args.timeframe:
        TIMEFRAME = args.timeframe
        # Map timeframe to freq if needed
        tf_map = {"1m": "1T", "5m": "5T", "15m": "15T", "30m": "30T", "1h": "1H", "4h": "4H", "1d": "1D"}
        FREQ = tf_map.get(TIMEFRAME, TIMEFRAME.upper())
        
    if args.run_id:
        RUN_ID = args.run_id
        
    # Set Results Dir based on Timeframe and RunID
    if RUN_ID != "Default":
        RESULTS_DIR = DOC_BASE / "Dokumentation" / "Fixed_Exit" / TIMEFRAME / RUN_ID
    else:
        # Fallback to simple timeframe folder if no ID provided (legacy behavior)
        RESULTS_DIR = DOC_BASE / "Dokumentation" / "Fixed_Exit" / TIMEFRAME
        
    if args.symbols:
        SYMBOLS = args.symbols.split(",")
        
    if args.start_date:
        DATE_START = args.start_date
        
    if args.end_date:
        DATE_END = args.end_date
        
    if args.capital:
        INITIAL_CAPITAL = args.capital
        
    print(f"Config: TF={TIMEFRAME}, Cap={INITIAL_CAPITAL}, Range={DATE_START} to {DATE_END}")
    
    if not args.scripts:
        print("No scripts provided.")
        return

    queue = args.scripts.split(",")
    print(f"Processing {len(queue)} indicators...")
        
    spreads, data_cache = load_data()
    
    for ind in queue:
        res = process_indicator(ind, spreads, data_cache)
        print(f"[W{args.worker_id}] {res}")

if __name__ == "__main__":
    main()
