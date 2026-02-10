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

# Settings
TIMEFRAME = "30m"
FREQ = "30min"

# Output Paths
RESULTS_DIR = DOC_BASE / "Dokumentation" / "Fixed_Exit" / TIMEFRAME
CHECKPOINT_DIR = DOC_BASE / "Dokumentation" / "Fixed_Exit" / TIMEFRAME / "00_checkpoint"
LOG_DIR = DOC_BASE / "LOG" / TIMEFRAME
LOG_DIR.mkdir(parents=True, exist_ok=True)

# LOG FILES
LOG_SUCCESS = LOG_DIR / "indicators_successful_backtested.log"
LOG_ERROR = LOG_DIR / "indicators_errors.log"
LOG_TIMEOUT = LOG_DIR / "indicators_timeout.log"
LOG_NO_RESULTS = LOG_DIR / "indicators_no_results.log"
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

def worker_process(ind_name, spreads, data_cache, queue, worker_id):
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
        
        res = run_indicator_logic(ind_name, spreads, data_cache, worker_id)
        queue.put(res)
    except Exception as e:
        queue.put(f"[FATAL-WORKER] {e}")

def log_status(fp, indicator, status, duration=0, details=""):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "indicator": indicator,
        "status": status,
        "duration_seconds": round(duration, 2),
        "details": str(details)
    }
    try:
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass

def run_indicator_logic(ind_name, spreads, data_cache, worker_id):
    # This is the actual calculation logic extracted from process_indicator
    try:
        try:
            ind_num = int(ind_name.split("_")[0])
        except:
            return f"[SKIP] Invalid name {ind_name}"
            
        # Checkpoint Init
        checkpoint_file = CHECKPOINT_DIR / f"worker_{worker_id}_checkpoint.json"
            
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
        last_checkpoint_time = start_time
        
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
                    
                    # Checkpoint Update (every 20s or iteration)
                    if time.time() - last_checkpoint_time > 10:
                        try:
                            cp_data = {
                                "strategy_num": ind_num,
                                "strategy_name": ind_name,
                                "start_time": start_time,
                                "current_combo": total_tests_run + symbol_tests_run,
                                "total_combos": limit, # Estimate
                                "last_update": time.time(),
                                "best_return": max([r["Total_Return"] for r in all_rows], default=0) if all_rows else 0,
                                "best_dd": min([r["Max_Drawdown"] for r in all_rows], default=0) if all_rows else 0,
                                "best_winrate": max([r["Win_Rate_%"] for r in all_rows], default=0) if all_rows else 0,
                                "best_trades": max([r["Total_Trades"] for r in all_rows], default=0) if all_rows else 0,
                                "best_pf": max([r["Profit_Factor"] for r in all_rows], default=0) if all_rows else 0,
                                "best_sharpe": max([r["Sharpe_Ratio"] for r in all_rows], default=0) if all_rows else 0,
                            }
                            with open(checkpoint_file, "w") as f:
                                json.dump(cp_data, f)
                            last_checkpoint_time = time.time()
                        except: pass

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
                    
                    # Robust extraction of entries
                    if isinstance(signals, dict):
                        if "entries" in signals:
                            entries = signals["entries"]
                        elif "Entries" in signals:
                            entries = signals["Entries"]
                        else:
                            # Fallback: assume the dict might contain Series/Arrays directly if not keyed
                            raise ValueError(f"Signals dict missing 'entries' key. Keys: {list(signals.keys())}")
                    else:
                        entries = signals

                    if hasattr(entries, "values"):
                        entries = entries.values
                    
                    if not isinstance(entries, np.ndarray):
                        entries = np.array(entries)

                    if entries.ndim > 1:
                        entries = entries.flatten()

                    if len(entries) != len(df):
                         raise ValueError(f"Entries length {len(entries)} != DF length {len(df)}")

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
            
            # LOG SUCCESS
            log_status(LOG_SUCCESS, ind_name, "SUCCESS", duration, f"Combos: {len(df_out)}")
            
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
            duration = time.time() - start_time
            log_status(LOG_NO_RESULTS, ind_name, "NO_RESULTS", duration, "0 combos generated")
            return f"[{datetime.now().strftime('%H:%M:%S')}] [{ind_num:03d}] [{ind_name}] NO RESULTS ({int(duration)}s)"
            
    except Exception as e:
        duration = time.time() - start_time
        log_status(LOG_ERROR, ind_name, "ERROR", duration, str(e))
        return f"[FATAL] {ind_name} crashed: {e}"

def process_indicator(ind_name, spreads, data_cache, worker_id):
    # Wrapper that uses multiprocessing to enforce HARD TIMEOUT
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=worker_process, args=(ind_name, spreads, data_cache, q, worker_id))
    p.start()
    p.join(timeout=TIMEOUT_SEC)
    
    if p.is_alive():
        p.terminate()
        # Give it a second
        time.sleep(1)
        if p.is_alive():
            p.kill() # Hard kill (SIGKILL)
        print(f"[TIMEOUT] {ind_name} killed after {TIMEOUT_SEC}s")
        log_status(LOG_TIMEOUT, ind_name, "TIMEOUT", TIMEOUT_SEC, "Process killed")
        return f"[TIMEOUT] {ind_name} killed"
    
    if not q.empty():
        return q.get()
    else:
        return f"[ERR] {ind_name} process finished but returned no result"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts", type=str, help="Comma-separated list of scripts to process")
    parser.add_argument("--worker-id", type=int, default=0, help="ID of this worker node")
    args = parser.parse_args()

    print(f"=== WORKER {args.worker_id} STARTED ===")
    
    if not args.scripts:
        print("No scripts provided.")
        return

    queue = args.scripts.split(",")
    print(f"Processing {len(queue)} indicators...")
        
    spreads, data_cache = load_data()
    
    # Checkpoint Dir Ensure
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    
    for ind in queue:
        # Pass worker_id to process_indicator
        res = process_indicator(ind, spreads, data_cache, args.worker_id)
        print(f"[W{args.worker_id}] {res}")

if __name__ == "__main__":
    main()
