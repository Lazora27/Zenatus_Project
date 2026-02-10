# -*- coding: utf-8 -*-
"""
PRODUCTION BACKTEST - 1H TIMEFRAME - ADAPTIVE 360
"""
import os
import sys
from pathlib import Path
import time
import pandas as pd
import numpy as np
import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime
import json

try:
    import vectorbt as vbt
except:
    print("vectorbt not installed!")
    sys.exit(1)

BASE_PATH = Path("/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys"
DATA_PATH = BASE_PATH / "99_Historic_Data" / "Forex" / "Major"
OUTPUT_ROOT = Path("/opt/Zenatus_Dokumentation") / "Dokumentation" / "Fixed_Exit" / "1h" / "03_02_2026" / "EURUSD"
SPREADS_PATH = BASE_PATH / "00_Backtester" / "Spreads"
PARAM_OPT_PATH = BASE_PATH / "01_Strategy" / "Parameter_Optimization"
HANDBOOK_JSON = PARAM_OPT_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
SUMMARY_CSV = PARAM_OPT_PATH / "PARAMETER_SUMMARY.csv"
QUICKTEST_RESULTS = BASE_PATH / "01_Backtest_System" / "QUICKTEST_RESULTS.json"

TIMEFRAME = '1h'
FREQ = '1H'
SYMBOLS = ['EUR_USD']
DATE_START = '2023-01-01'
DATE_END = '2026-01-01'
INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
INDICATOR_TIMEOUT = 1800
MAX_WORKERS = max(1, os.cpu_count() or 4)
SLIPPAGE_PIPS = 0.5
COMMISSION_PER_LOT = 3.0
pip_value = 0.0001

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

spreads_df = pd.read_csv(SPREADS_PATH / "FTMO_SPREADS_FOREX.csv")
SPREADS = {row['Symbol'].replace('/', '_'): row['Typical_Spread_Pips'] for _, row in spreads_df.iterrows()}

DATA_CACHE = {}
for symbol in SYMBOLS:
    fp = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
    if not fp.exists():
        continue
    df = pd.read_csv(fp)
    df.columns = [c.lower() for c in df.columns]
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
    DATA_CACHE[symbol] = {'full': df}

with open(HANDBOOK_JSON, 'r', encoding='utf-8') as f:
    HANDBOOK_DATA = json.load(f)
HANDBOOK_INDEX = {int(item["Indicator_Num"]): item for item in HANDBOOK_DATA}
SUMMARY_DF = pd.read_csv(SUMMARY_CSV)
SUMMARY_DF["Indicator_Num"] = SUMMARY_DF["Indicator_Num"].astype(int)
SUMMARY_IDX = SUMMARY_DF.set_index("Indicator_Num")

if QUICKTEST_RESULTS.exists():
    with open(QUICKTEST_RESULTS, 'r', encoding='utf-8') as f:
        qt = json.load(f)
    SUCCESS_INDICATORS = sorted([int(x) for x in qt.get("SUCCESS", []) if int(x) in HANDBOOK_INDEX])
else:
    SUCCESS_INDICATORS = sorted(HANDBOOK_INDEX.keys())

def calculate_metrics(pf, spread_pips):
    trades = pf.trades.count()
    if trades < 3:
        return None
    total_return = pf.total_return() * 100
    max_dd = abs(pf.max_drawdown()) * 100
    win_rate = pf.trades.win_rate() * 100
    profit_factor = pf.trades.profit_factor()
    sharpe = pf.sharpe_ratio()
    total_profit = pf.total_profit()
    equity = pf.value()
    equity_daily = equity.resample('D').last().dropna()
    if len(equity_daily) > 1:
        cummax = equity_daily.expanding().max()
        daily_drawdowns = (equity_daily - cummax) / cummax
        daily_dd = abs(daily_drawdowns.min()) * 100
    else:
        daily_dd = max_dd
    lot_size = POSITION_SIZE / 100000
    total_commission = trades * COMMISSION_PER_LOT * lot_size
    net_profit = total_profit - total_commission
    net_return = (net_profit / INITIAL_CAPITAL) * 100
    wins = pf.trades.winning
    losses = pf.trades.losing
    avg_win = float(wins.pnl.mean()) if wins.count() > 0 else 0.0
    avg_loss = float(losses.pnl.mean()) if losses.count() > 0 else 0.0
    highest_win = float(wins.pnl.max()) if wins.count() > 0 else 0.0
    highest_loss = float(losses.pnl.min()) if losses.count() > 0 else 0.0
    if np.isnan(profit_factor) or np.isinf(profit_factor):
        profit_factor = 0.0
    if np.isnan(sharpe) or np.isinf(sharpe):
        sharpe = 0.0
    return {
        'Total_Return': float(f"{net_return:.4f}"),
        'Max_Drawdown': float(f"{max_dd:.4f}"),
        'Daily_Drawdown': float(f"{daily_dd:.4f}"),
        'Win_Rate_%': float(f"{win_rate:.2f}"),
        'Total_Trades': int(trades),
        'Winning_Trades': int(wins.count()),
        'Losing_Trades': int(losses.count()),
        'Avg_Win': float(f"{avg_win:.6f}"),
        'Avg_Loss': float(f"{avg_loss:.6f}"),
        'Highest_Win': float(f"{highest_win:.6f}"),
        'Highest_Loss': float(f"{highest_loss:.6f}"),
        'Gross_Profit': float(f"{total_profit:.6f}"),
        'Commission': float(f"{total_commission:.6f}"),
        'Net_Profit': float(f"{net_profit:.6f}"),
        'Profit_Factor': float(f"{profit_factor:.3f}"),
        'Sharpe_Ratio': float(f"{sharpe:.3f}")
    }

def backtest_batch_combinations(df, entries, tp_sl_combos, spread_pips):
    try:
        tp_array = []
        sl_array = []
        valid_combos = []
        for tp_pips, sl_pips in tp_sl_combos:
            effective_tp = (tp_pips - spread_pips - SLIPPAGE_PIPS) * pip_value
            effective_sl = (sl_pips + spread_pips + SLIPPAGE_PIPS) * pip_value
            if effective_tp > 0 and effective_sl > 0:
                tp_array.append(effective_tp)
                sl_array.append(effective_sl)
                valid_combos.append((tp_pips, sl_pips))
        if not valid_combos:
            return []
        pf = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries,
            exits=False,
            tp_stop=tp_array,
            sl_stop=sl_array,
            init_cash=INITIAL_CAPITAL,
            size=POSITION_SIZE,
            size_type='amount',
            fees=0.0,
            freq=FREQ
        )
        results = []
        for idx, (tp_pips, sl_pips) in enumerate(valid_combos):
            try:
                pf_single = pf[idx] if len(valid_combos) > 1 else pf
                metrics = calculate_metrics(pf_single, spread_pips)
                if metrics:
                    metrics['TP_Pips'] = tp_pips
                    metrics['SL_Pips'] = sl_pips
                    results.append(metrics)
            except:
                continue
        return results
    except:
        return []

def build_periods_and_combos(ind_num):
    hb = HANDBOOK_INDEX.get(ind_num, {})
    entry_cfg = hb.get('Entry_Params', {})
    exit_cfg = hb.get('Exit_Params', {})
    period_values = []
    if 'period' in entry_cfg:
        vals = entry_cfg['period'].get('values', [])
        if isinstance(vals, list) and len(vals) > 0:
            period_values = vals
    if not period_values:
        period_values = [10, 14, 20, 30, 50]
    tp_values = exit_cfg.get('tp_pips', {}).get('values', [50, 75, 100, 125, 150])
    sl_values = exit_cfg.get('sl_pips', {}).get('values', [30, 40, 50, 60, 75])
    total_summary = SUMMARY_IDX.loc[ind_num]['Total_Combinations'] if ind_num in SUMMARY_IDX.index else 3120
    if total_summary <= 3120:
        target = 3120
    elif total_summary <= 5000:
        target = 5000
    else:
        target = 10000
    combos = [(tp, sl) for tp in tp_values for sl in sl_values]
    period_count = len(period_values)
    per_period_budget = max(1, target // max(1, period_count))
    return period_values, combos[:per_period_budget]

def test_indicator(ind_file):
    ind_name = ind_file.stem
    try:
        ind_num = int(ind_name.split('_')[0])
    except:
        return None
    start_time = time.time()
    try:
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        indicator_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and (attr_name.startswith('Indicator_') or attr_name.endswith('Indicator')):
                indicator_class = attr
                break
        if not indicator_class:
            return None
        ind_instance = indicator_class()
        period_values, tp_sl_base = build_periods_and_combos(ind_num)
        all_rows = []
        for symbol in SYMBOLS:
            if symbol not in DATA_CACHE:
                continue
            spread_pips = SPREADS.get(symbol, 2.0)
            df_full = DATA_CACHE[symbol]['full']
            best_sr = -999
            for period in period_values:
                try:
                    signals_full = None
                    try:
                        signals_full = ind_instance.generate_signals_fixed(df_full, {'period': period})
                    except TypeError:
                        try:
                            signals_full = ind_instance.generate_signals_fixed(df_full, {'period': period, 'vfactor': 0.7})
                        except:
                            signals_full = ind_instance.generate_signals_fixed(df_full, {})
                    entries_full = signals_full['entries'].values
                    if isinstance(entries_full, np.ndarray):
                        entries_full = pd.Series(entries_full, index=df_full.index)
                    entries_full = entries_full.fillna(False).astype(bool)
                    if entries_full.sum() < 3:
                        continue
                    batch_results = backtest_batch_combinations(df_full, entries_full, tp_sl_base, spread_pips)
                    if not batch_results:
                        continue
                    for metrics_full in batch_results:
                        if metrics_full['Sharpe_Ratio'] > best_sr:
                            best_sr = metrics_full['Sharpe_Ratio']
                        row_full = {
                            'Indicator_Num': ind_num,
                            'Indicator': ind_name,
                            'Symbol': symbol,
                            'Timeframe': TIMEFRAME,
                            'TP_Pips': metrics_full['TP_Pips'],
                            'SL_Pips': metrics_full['SL_Pips'],
                            'Spread_Pips': spread_pips,
                            'Slippage_Pips': SLIPPAGE_PIPS,
                            'Entry_period': period
                        }
                        for key in ['Total_Return','Max_Drawdown','Daily_Drawdown','Win_Rate_%',
                                    'Total_Trades','Winning_Trades','Losing_Trades','Avg_Win','Avg_Loss',
                                    'Highest_Win','Highest_Loss','Gross_Profit','Commission','Net_Profit',
                                    'Profit_Factor','Sharpe_Ratio']:
                            if key in metrics_full:
                                row_full[key] = metrics_full[key]
                        all_rows.append(row_full)
                except:
                    continue
        elapsed = time.time() - start_time
        if len(all_rows) > 0:
            output_file = OUTPUT_ROOT / f"{ind_num:03d}_{ind_name}_{SYMBOLS[0]}_{TIMEFRAME}_{DATE_START.replace('-','')}_{DATE_END.replace('-','')}.csv"
            df_results = pd.DataFrame(all_rows)
            df_results.to_csv(output_file, index=False, float_format='%.6f')
        return (ind_num, len(all_rows), elapsed)
    except Exception as e:
        return None

all_indicators = sorted(INDICATORS_PATH.glob("*.py"))
success_set = set(SUCCESS_INDICATORS)
filtered_indicators = [ind for ind in all_indicators if int(ind.stem.split('_')[0]) in success_set]

start_time = time.time()
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(test_indicator, ind_file): ind_file for ind_file in filtered_indicators}
    for future in as_completed(futures):
        try:
            res = future.result(timeout=INDICATOR_TIMEOUT)
            if res:
                ind_num, rows_count, elapsed_ind = res
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Ind#{ind_num:03d} | rows={rows_count} | {elapsed_ind:.1f}s")
        except TimeoutError:
            ind_file = futures[future]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] TIMEOUT {ind_file.stem}")
        except Exception:
            pass

elapsed = time.time() - start_time
print(f"COMPLETE | Indicators: {len(filtered_indicators)} | {elapsed/60:.2f} min")
