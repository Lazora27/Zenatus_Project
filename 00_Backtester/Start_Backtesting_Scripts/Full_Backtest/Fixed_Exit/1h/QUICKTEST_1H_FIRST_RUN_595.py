# -*- coding: utf-8 -*-
import sys
import json
import time
import re
import csv
import os
import argparse
import subprocess
import threading
from queue import Queue, Empty
from pathlib import Path
from datetime import datetime
import concurrent.futures
import pandas as pd
import numpy as np
import importlib.util

# Add agent path to sys.path to import config
sys.path.append(os.path.join(os.environ.get("ZENATUS_BASE_PATH", "/opt/Zenatus_Backtester"), "02_Agents"))
try:
    from config_loader import config
    from logger_setup import logger
except ImportError:
    # Fallback if path is wrong
    class ConfigMock:
        def get(self, *args): return None
        @property
        def paths(self): return {}
    config = ConfigMock()
    import logging
    logger = logging.getLogger("fallback")

BASE_PATH = config.paths.get("base") or Path(os.environ.get("ZENATUS_BASE_PATH", r"/opt/Zenatus_Backtester"))
INDICATORS_PATH = config.paths.get("strategies") or BASE_PATH / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys"
DATA_PATH = config.paths.get("data") or BASE_PATH / "99_Historic_Data"
if not str(DATA_PATH).endswith("Forex/Major"): # Fallback structure fix
     DATA_PATH = DATA_PATH / "Forex" / "Major"
     
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
SPREADS_PATH = BASE_PATH / "00_Backtester" / "Spreads"
PARAM_OPT_PATH = BASE_PATH / "01_Strategy" / "Parameter_Optimization"
DOC_BASE = config.paths.get("documentation") or Path(r"/opt/Zenatus_Dokumentation")
LOG_DIR = config.paths.get("logs") / "1h" if config.paths.get("logs") else DOC_BASE / "LOG" / "1h"
LISTING_DIR = config.paths.get("listings") / "Quicktest" / "1h" if config.paths.get("listings") else DOC_BASE / "Listing" / "Quicktest" / "1h"
SUCCESS_LISTING_FILE = LISTING_DIR / "indicators_succesful_backtested.json"
BRIDGE_SCRIPT = BASE_PATH / "02_Agents" / "bridge_agent.py"
LOG_FILES = {
    "ALL": LOG_DIR / "indicators_all.log",
    "ERROR": LOG_DIR / "indicators_errors.log",
    "NO_RESULTS": LOG_DIR / "indicators_no_results.log",
    "SUCCESS": LOG_DIR / "indicators_successful_backtested.log",
    "TIMEOUT": LOG_DIR / "indicators_timeout.log",
    "WARNING": LOG_DIR / "indicators_warnings.log",
    "WORKING": LOG_DIR / "indicators_working.log",
}

TIMEFRAME = "1h"
FREQ = "1H"
SYMBOLS = ["EUR_USD"]
DATE_START = "2024-01-01"
DATE_END = "2025-01-01"
INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
SLIPPAGE_PIPS = 0.5
COMMISSION_PER_LOT = 3.0
pip_value = 0.0001

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
        if "time" not in df.columns and "Time" in [c for c in df.columns]:
            df.rename(columns={"Time": "time"}, inplace=True)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
        cache[symbol] = {"full": df}
        print(f"[DATA] {symbol} bars={len(df)}")
    return spreads, cache

def select_two_combos(ind_num, ind_name):
    handbook_file = PARAM_OPT_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
    summary_file = PARAM_OPT_PATH / "PARAMETER_SUMMARY.csv"
    tp_sl = []
    if handbook_file.exists():
        try:
            with open(handbook_file, "r", encoding="utf-8") as f:
                hb = json.load(f)
            # Handbook is a list of dicts
            entry = None
            if isinstance(hb, list):
                for item in hb:
                    if str(item.get("Indicator_Num")) == str(ind_num):
                        entry = item
                        break
            elif isinstance(hb, dict):
                entry = hb.get(str(ind_num))
            
            if entry:
                # Handle both structures (Exit_Params or direct)
                exit_params = entry.get("Exit_Params", entry)
                tp_values = exit_params.get("tp_pips", {}).get("values", [])
                sl_values = exit_params.get("sl_pips", {}).get("values", [])
                
                for tp in tp_values:
                    for sl in sl_values:
                        if tp > sl:
                            tp_sl.append((tp, sl))
        except Exception as e:
            print(f"[WARN] Handbook load error: {e}")
            pass
    if not tp_sl and summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        tp = int(float(row.get("tp_pips", "0")))
                        sl = int(float(row.get("sl_pips", "0")))
                        if tp > 0 and sl > 0 and tp > sl:
                            tp_sl.append((tp, sl))
                    except:
                        continue
        except:
            pass
    if not tp_sl:
        # FALLBACK TRIGGERED
        tp_sl = [(50, 30), (100, 60)]
        write_jsonl(LOG_FILES["WARNING"], {
            "indicator": ind_name, 
            "reason": "WARNING_FALLBACK_PARAMS", 
            "msg": "Using default (50,30), (100,60) combos",
            "ts": datetime.utcnow().isoformat()
        })
    return tp_sl[:2]

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
    vals = {
        "Total_Trades": int(trades),
        "Total_Return": float(f"{net_return:.4f}"),
        "Max_Drawdown": float(f"{max_dd:.4f}"),
        "Win_Rate_%": float(f"{win_rate:.2f}"),
        "Profit_Factor": float(f"{0.0 if np.isnan(pfactor) or np.isinf(pfactor) else pfactor:.3f}"),
        "Sharpe_Ratio": float(f"{0.0 if np.isnan(sharpe) or np.isinf(sharpe) else sharpe:.3f}"),
        "TP_Pips": tp_pips,
        "SL_Pips": sl_pips
    }
    return vals

def format_hms(seconds):
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    ss = s % 60
    return f"{h:02d}h/{m:02d}m/{ss:02d}s"

def print_progress(ind_num, ind_name, combos_count, best_metrics, elapsed_sec):
    ts = datetime.now().strftime("%H:%M:%S")
    if best_metrics:
        ret_val = best_metrics.get("Total_Return")
        dd_val = best_metrics.get("Max_Drawdown")
        pf_val = best_metrics.get("Profit_Factor")
        sh_val = best_metrics.get("Sharpe_Ratio")
        trades_val = best_metrics.get("Total_Trades")
        ret = f"{ret_val:.2f}%" if ret_val is not None else "NA"
        dd = f"{dd_val:.2f}%" if dd_val is not None else "NA"
        pf = f"{pf_val:.3f}" if pf_val is not None else "NA"
        sh = f"{sh_val:.3f}" if sh_val is not None else "NA"
        trades = int(trades_val) if trades_val is not None else 0
    else:
        ret = "NA"
        dd = "NA"
        pf = "NA"
        sh = "NA"
        trades = 0
    duration = format_hms(elapsed_sec)
    print(f"[{ts}] [{ind_num:03d}] [{ind_name}] [{TIMEFRAME}] [Combi={combos_count}] [Results: Return={ret} / DD={dd} / Profitfactor={pf} / Sharp={sh} / Trades={trades}] [{duration}]")

def batch_backtest(df, entries, tp_sl_combos, spread_pips):
    tp_array = []
    sl_array = []
    valid = []
    for tp_pips, sl_pips in tp_sl_combos:
        effective_tp = (tp_pips - spread_pips - SLIPPAGE_PIPS) * pip_value
        effective_sl = (sl_pips + spread_pips + SLIPPAGE_PIPS) * pip_value
        if effective_tp > 0 and effective_sl > 0:
            tp_array.append(effective_tp)
            sl_array.append(effective_sl)
            valid.append((tp_pips, sl_pips))
    if not valid:
        return []
    tp_array = np.array(tp_array)
    sl_array = np.array(sl_array)
    if len(valid) == 1:
        close_in = df["close"]
        entries_in = entries
        tp_in = tp_array
        sl_in = sl_array
    else:
        close_in = pd.concat([df["close"]]*len(valid), axis=1)
        close_in.columns = [f"combo_{i}" for i in range(len(valid))]
        entries_in = pd.concat([entries]*len(valid), axis=1)
        entries_in.columns = [f"combo_{i}" for i in range(len(valid))]
        tp_in = tp_array
        sl_in = sl_array
    pf = vbt.Portfolio.from_signals(
        close=close_in,
        entries=entries_in,
        exits=False,
        tp_stop=tp_in,
        sl_stop=sl_in,
        init_cash=INITIAL_CAPITAL,
        size=POSITION_SIZE,
        size_type="amount",
        fees=0.0,
        freq=FREQ
    )
    results = []
    for idx, (tp_pips, sl_pips) in enumerate(valid):
        col = f"combo_{idx}"
        pf_single = pf[col] if len(valid) > 1 else pf
        m = calculate_metrics(pf_single, spread_pips, tp_pips, sl_pips)
        if m:
            results.append(m)
    return results

def run_indicator(ind_path, spreads, data_cache):
    ind_name = ind_path.stem
    try:
        ind_num = int(ind_name.split("_")[0])
    except:
        print(f"[ERROR] invalid indicator name {ind_name}")
        return None
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
        print(f"[ERROR] class not found {ind_name}")
        return None

    combos = select_two_combos(ind_num, ind_name)
    combos_count = len(combos)
    all_rows = []
    start = time.time()

    for symbol in SYMBOLS:
        if symbol not in data_cache:
            continue
        df = data_cache[symbol]["full"]
        spread_pips = spreads.get(symbol, 2.0)
        instance = klass()
        try:
            signals = instance.generate_signals_fixed(df, {})
        except:
            signals = instance.generate_signals_fixed(df, {})
        entries = signals["entries"].values
        if isinstance(entries, np.ndarray):
            entries = pd.Series(entries, index=df.index)
        entries = entries.fillna(False).astype(bool)
        if entries.sum() < 1:
            continue
        res = batch_backtest(df, entries, combos, spread_pips)
        for r in res:
            row = {
                "Indicator_Num": ind_num,
                "Indicator": ind_name,
                "Symbol": symbol,
                "Timeframe": TIMEFRAME,
                "Spread_Pips": spread_pips,
                "Slippage_Pips": SLIPPAGE_PIPS
            }
            row.update(r)
            all_rows.append(row)
    elapsed = time.time() - start

    out_dir = DOC_BASE / "Dokumentation" / "Quick_Test" / TIMEFRAME
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{ind_num:03d}_{ind_name}.csv"
    if len(all_rows) > 0:
        pd.DataFrame(all_rows).to_csv(out_file, index=False, float_format="%.6f")
        best = max(all_rows, key=lambda x: x.get("Sharpe_Ratio", -999))
        print_progress(ind_num, ind_name, combos_count, best, elapsed)
    else:
        print_progress(ind_num, ind_name, combos_count, None, elapsed)
    return {"rows": len(all_rows), "elapsed_sec": int(elapsed), "csv": str(out_file)}

class Streamer:
    def __init__(self, pipe, sink_fp):
        self.pipe = pipe
        self.sink_fp = sink_fp
        self.lines = []
        self.thread = threading.Thread(target=self._run, daemon=True)
    def start(self):
        self.thread.start()
    def _run(self):
        self.sink_fp.parent.mkdir(parents=True, exist_ok=True)
        with open(self.sink_fp, "a", encoding="utf-8") as f:
            for line in iter(self.pipe.readline, b""):
                try:
                    s = line.decode("utf-8", errors="ignore").rstrip("\r\n")
                except:
                    s = str(line).rstrip("\r\n")
                self.lines.append(s)
                f.write(s + "\n")
        self.pipe.close()
    def join(self):
        self.thread.join()

class Runner:
    def __init__(self, indicator_path, timeout_sec=900, inactivity_sec=30):
        self.indicator_path = Path(indicator_path)
        self.timeout_sec = timeout_sec
        self.inactivity_sec = inactivity_sec

    def run(self):
        raw_dir = LOG_DIR / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base = self.indicator_path.stem
        stdout_fp = raw_dir / f"{base}.{stamp}.stdout.log"
        stderr_fp = raw_dir / f"{base}.{stamp}.stderr.log"
        cmd = [sys.executable, str(Path(__file__)), str(self.indicator_path)]
        t0 = time.time()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_stream = Streamer(p.stdout, stdout_fp)
        err_stream = Streamer(p.stderr, stderr_fp)
        out_stream.start()
        err_stream.start()
        
        ret = None
        last_activity = time.time()
        last_lines_count = 0
        
        while True:
            ret = p.poll()
            if ret is not None:
                break
            
            now = time.time()
            current_lines_count = len(out_stream.lines) + len(err_stream.lines)
            
            if current_lines_count > last_lines_count:
                last_activity = now
                last_lines_count = current_lines_count
            
            if (now - t0) > self.timeout_sec:
                try:
                    p.kill()
                except:
                    pass
                ret = None # Timeout
                break
                
            if (now - last_activity) > self.inactivity_sec:
                # Inactivity detected
                try:
                    p.kill()
                except:
                    pass
                ret = None # Treated as timeout/hang
                # Append a special log line to indicate inactivity kill
                try:
                    with open(stderr_fp, "a", encoding="utf-8") as f:
                        f.write(f"\n[WATCHDOG] Process killed due to inactivity (> {self.inactivity_sec}s)\n")
                    err_stream.lines.append(f"[WATCHDOG] Process killed due to inactivity (> {self.inactivity_sec}s)")
                except:
                    pass
                break
                
            time.sleep(1.0)

        out_stream.join()
        err_stream.join()
        t1 = time.time()
        return {
            "exit_code": p.returncode if ret is not None else None,
            "runtime_sec": int(t1 - t0),
            "stdout_lines": out_stream.lines,
            "stderr_lines": err_stream.lines,
            "stdout_fp": str(stdout_fp),
            "stderr_fp": str(stderr_fp),
        }

class Classifier:
    ERROR_PAT = re.compile(r"(Traceback|Error|Exception|FATAL|CRITICAL)", re.IGNORECASE)
    WARN_PAT = re.compile(r"(Warning|UserWarning|DeprecationWarning)", re.IGNORECASE)
    NORES_PAT = re.compile(r"NO_RESULTS", re.IGNORECASE)
    TRADES_PAT = re.compile(r"trades=?\s*(\d+)", re.IGNORECASE)
    NETRET_PAT = re.compile(r"Return=?\s*([\-+]?\d+(\.\d+)?)%?", re.IGNORECASE)
    MAXDD_PAT = re.compile(r"DD=?\s*([\-+]?\d+(\.\d+)?)%?", re.IGNORECASE)
    PF_PAT = re.compile(r"Profitfactor=([\-+]?\d+(\.\d+)?)", re.IGNORECASE)
    SH_PAT = re.compile(r"Sharp=([\-+]?\d+(\.\d+)?)", re.IGNORECASE)
    BARS_PAT = re.compile(r"bars=(\d+)", re.IGNORECASE)
    def classify(self, indicator_name, run_ret):
        exit_code = run_ret["exit_code"]
        runtime_sec = run_ret["runtime_sec"]
        lines = run_ret["stdout_lines"] + run_ret["stderr_lines"]
        text = "\n".join(lines)
        err_idx = None
        for i, s in enumerate(lines):
            if self.ERROR_PAT.search(s):
                err_idx = i
                break
        m_trades = self.TRADES_PAT.search(text)
        m_ret = self.NETRET_PAT.search(text)
        m_dd = self.MAXDD_PAT.search(text)
        m_pf = self.PF_PAT.search(text)
        m_sh = self.SH_PAT.search(text)
        trades = int(m_trades.group(1)) if m_trades else None
        net_ret = float(m_ret.group(1)) if m_ret else None
        max_dd = float(m_dd.group(1)) if m_dd else None
        profit_factor = float(m_pf.group(1)) if m_pf else None
        sharpe_ratio = float(m_sh.group(1)) if m_sh else None
        reason = None
        if exit_code is None or runtime_sec >= self_timeout_threshold():
            cat = "TIMEOUT"
            reason = "INDICATOR_EXECUTION_TIMEOUT"
        elif "data not found" in text.lower():
            cat = "ERROR"
            reason = "ERROR_DATA_FILE_NOT_FOUND"
        elif "data empty" in text.lower():
            cat = "ERROR"
            reason = "ERROR_DATA_EMPTY"
        elif "bad columns" in text.lower():
            cat = "ERROR"
            reason = "ERROR_DATA_BAD_COLUMNS"
        elif "time not sorted" in text.lower():
            cat = "ERROR"
            reason = "ERROR_DATA_TIME_NOT_SORTED"
        elif "nan" in text.lower() and "critical" in text.lower():
            cat = "ERROR"
            reason = "ERROR_DATA_NAN_CRITICAL"
        elif "class not found" in text.lower():
            cat = "ERROR"
            reason = "ERROR_INDICATOR_CLASS_NOT_FOUND"
        elif "invalid indicator name" in text.lower():
            cat = "ERROR"
            reason = "ERROR_INDICATOR_IMPORT_FAIL"
        elif "generate_signals_fixed" in text.lower() and "traceback" in text.lower():
            cat = "ERROR"
            reason = "ERROR_INDICATOR_GENERATE_FAIL"
        elif "no module named" in text.lower():
            cat = "ERROR"
            reason = "ERROR_INDICATOR_IMPORT_FAIL"
        elif "shape mismatch" in text.lower():
            cat = "ERROR"
            reason = "ERROR_BACKTEST_SIGNAL_SHAPE_MISMATCH"
        elif "portfolio.from_signals" in text.lower() or "vectorbt" in text.lower():
            if "traceback" in text.lower() or (exit_code and exit_code != 0):
                cat = "ERROR"
                reason = "ERROR_BACKTEST_ENGINE_CRASH"
            else:
                cat = "ERROR"
                reason = "ERROR_BACKTEST_PORTFOLIO_FAIL"
        elif exit_code and exit_code != 0:
            cat = "ERROR"
            reason = "ERROR_SYSTEM_UNKNOWN"
        elif self.NORES_PAT.search(text):
            cat = "NO_RESULTS"
            reason = "NO_TRADES_GENERATED"
        elif trades is not None and trades < 1:
            cat = "NO_RESULTS"
            reason = "NO_TRADES_GENERATED"
        elif "no valid tp" in text.lower():
            cat = "NO_RESULTS"
            reason = "NO_VALID_TP_SL_COMBOS"
        elif "signal all false" in text.lower():
            cat = "NO_RESULTS"
            reason = "SIGNAL_ALL_FALSE"
        elif self.WARN_PAT.search(text):
            cat = "WARNING"
            reason = "WARNING_DATA_RESAMPLE"
        else:
            cat = "SUCCESS"
        warn_reasons = []
        m_bars = self.BARS_PAT.search(text)
        if m_bars:
            bars = int(m_bars.group(1))
            if bars < 1000:
                warn_reasons.append("WARNING_DATA_FEW_BARS")
        if trades is not None and trades < 5:
            warn_reasons.append("WARNING_LOW_TRADES")
        if max_dd is not None and max_dd > 50:
            warn_reasons.append("WARNING_HIGH_DRAWDOWN")
        if net_ret is not None and net_ret < -50:
            warn_reasons.append("WARNING_HIGH_DRAWDOWN")
        if warn_reasons and cat == "SUCCESS":
            cat = "WARNING"
            if reason is None:
                reason = warn_reasons[0]
        if cat == "SUCCESS" and (trades is None or trades == 0):
            cat = "NO_RESULTS"
            reason = "NO_TRADES_GENERATED"
        info = {
            "indicator": indicator_name,
            "runtime_sec": runtime_sec,
            "exit_code": exit_code if exit_code is not None else -1,
            "trades": trades,
            "net_return": net_ret,
            "max_dd": max_dd,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "reason": reason,
            "warnings": warn_reasons,
            "error_snippet": lines[err_idx] if err_idx is not None else None,
            "stdout_fp": run_ret["stdout_fp"],
            "stderr_fp": run_ret["stderr_fp"],
        }
        return cat, info

def self_timeout_threshold():
    return 900

def write_jsonl(target_fp, obj):
    Path(target_fp).parent.mkdir(parents=True, exist_ok=True)
    with open(target_fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def sync_success_listing():
    src_dir = DOC_BASE / "Dokumentation" / "Fixed_Exit" / TIMEFRAME
    names = []
    for fp in src_dir.glob("*.csv"):
        names.append(fp.stem)
    names = sorted(set(names))
    LISTING_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"scripts": names}
    with open(SUCCESS_LISTING_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(names)

def get_processed_indicators():
    processed = set()
    # Check these categories for completed runs
    for key in ["SUCCESS", "ERROR", "TIMEOUT", "NO_RESULTS", "WARNING"]:
        fp = LOG_FILES.get(key)
        if not fp or not fp.exists():
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        obj = json.loads(line)
                        if "indicator" in obj:
                            processed.add(obj["indicator"])
                    except:
                        pass
        except:
            pass
    return processed

def validate_all(timeout_sec=900, limit=None, workers=0):
    inds = sorted(INDICATORS_PATH.glob("*.py"))
    
    # --- RESUME LOGIC ---
    done_inds = get_processed_indicators()
    if done_inds:
        print(f"[RESUME] Found {len(done_inds)} already processed indicators. Skipping them.")
        inds = [i for i in inds if i.stem not in done_inds]
    else:
        print("[RESUME] No previous progress found (or logs empty). Starting from scratch.")
    # --------------------

    if limit is not None:
        inds = inds[:limit]
    if not inds:
        print("[INFO] No indicators to run (all done or limit reached).")
        return
    max_workers = workers if workers and workers > 0 else (os.cpu_count() or 1)
    max_workers = max(1, min(max_workers, len(inds)))
    print(f"[INFO] Running {len(inds)} indicators with {max_workers} workers.")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for ind in inds:
            ind_name = ind.stem
            try:
                ind_num = int(ind_name.split("_")[0])
            except:
                ind_num = 0
            combos_count = len(select_two_combos(ind_num, ind_name)) if ind_num else 0
            write_jsonl(LOG_FILES["ALL"], {"indicator": ind_name, "status": "STARTED", "ts": datetime.utcnow().isoformat()})
            write_jsonl(LOG_FILES["WORKING"], {"indicator": ind_name, "status": "RUNNING", "ts": datetime.utcnow().isoformat()})
            fut = executor.submit(Runner(ind, timeout_sec=timeout_sec).run)
            futures[fut] = (ind_name, ind_num, combos_count)
        for fut in concurrent.futures.as_completed(futures):
            ind_name, ind_num, combos_count = futures[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {
                    "exit_code": 1,
                    "runtime_sec": 0,
                    "stdout_lines": [],
                    "stderr_lines": [str(e)],
                    "stdout_fp": "",
                    "stderr_fp": "",
                }
            cat, info = Classifier().classify(ind_name, r)
            write_jsonl(LOG_FILES[cat], info)
            metrics = {
                "Total_Return": info.get("net_return"),
                "Max_Drawdown": info.get("max_dd"),
                "Profit_Factor": info.get("profit_factor"),
                "Sharpe_Ratio": info.get("sharpe_ratio"),
                "Total_Trades": info.get("trades"),
            }
            print_progress(ind_num if ind_num else 0, ind_name, combos_count, metrics, info.get("runtime_sec", 0))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-all", action="store_true")
    parser.add_argument("--sync-success-listing", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("indicator", nargs="?", default=None)
    args = parser.parse_args()
    if args.sync_success_listing:
        n = sync_success_listing()
        print(f"[SYNC] successful_backtested count={n}")
        return
    ind_arg = Path(args.indicator) if args.indicator else None
    if args.validate_all:
        validate_all(timeout_sec=args.timeout_sec, limit=args.limit, workers=args.workers)
        return
    spreads, data_cache = load_data()
    if ind_arg and ind_arg.exists():
        run_indicator(ind_arg, spreads, data_cache)
    else:
        validate_all(timeout_sec=args.timeout_sec, limit=args.limit, workers=args.workers)
        
    # Trigger Bridge Agent
    if BRIDGE_SCRIPT.exists():
        print(f"[BRIDGE] Running bridge agent: {BRIDGE_SCRIPT}")
        try:
            subprocess.run([sys.executable, str(BRIDGE_SCRIPT)], check=False)
        except Exception as e:
            print(f"[BRIDGE] Error running bridge: {e}")
            
    time.sleep(1)

if __name__ == "__main__":
    main()
