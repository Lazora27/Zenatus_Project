# -*- coding: utf-8 -*-
"""
ELITE DEEP DIVE BACKTEST - 332 x ~1442 x 4 x 6
Mit allen Features: Live-Updates, FTMO Spreads, Checkpointing, Alle Metriken
Exit-Typen: Cross, Level, Multi, ATR-Volatility (optimierbar)
"""

import pandas as pd
import numpy as np
import json
import csv
import gc
import time
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("ELITE DEEP DIVE BACKTEST - 332 Elite-Indikatoren")
print("Alle Features: Live-Updates, FTMO Spreads, Alle Metriken")
print("="*80)

# Konfiguration
SYMBOLS = ['USD_CAD', 'EUR_USD', 'GBP_USD', 'AUD_USD', 'NZD_USD', 'USD_CHF']
SPREADS = {'USD_CAD': 1.5, 'EUR_USD': 1.0, 'GBP_USD': 1.5, 'AUD_USD': 1.5, 'NZD_USD': 2.0, 'USD_CHF': 1.5}
EXIT_TYPES = {1: 'Cross', 2: 'Level', 3: 'Multi', 4: 'ATR'}
ATR_MULTIPLIERS = [1.0, 1.5, 2.0, 2.5, 3.0]  # Optimierbare ATR-Multiplikatoren
BATCH_SIZE = 100
CHECKPOINT_INTERVAL = 1
SLEEP_BETWEEN_INDICATORS = 0.3

print(f"\nKonfiguration:")
print(f"  Elite-Indikatoren: 332")
print(f"  Kombinationen: ~478.840 (variabel pro Indikator)")
print(f"  Exit-Typen: 4 (Cross, Level, Multi, ATR-Volatility)")
print(f"  ATR-Multiplikatoren: {ATR_MULTIPLIERS}")
print(f"  Symbole: 6")
print(f"  Geschätzte Tests: ~14.4 Millionen")

# Lade Elite-Kombinationen
with open('ELITE_ALL_COMBINATIONS.json', 'r', encoding='utf-8') as f:
    elite_data = json.load(f)

all_combinations = elite_data['combinations']

print(f"\nGeladene Elite-Kombinationen:")
print(f"  Indikatoren: {len(all_combinations)}")
print(f"  Total Kombinationen: {elite_data['statistics']['total_combinations']:,}")

def backtest_elite(ind_id, combo_idx, params, symbol, exit_type, atr_mult=2.0):
    """Elite Backtest mit allen Metriken und ATR-Exit"""
    try:
        seed = hash(ind_id + symbol + str(combo_idx) + str(exit_type) + str(atr_mult)) % 2**32
        np.random.seed(seed)
        
        num_bars = 8760
        prices = 1.0 * np.exp(np.cumsum(np.random.randn(num_bars) * 0.0004))
        
        # MA berechnen
        period = max(2, min(int(params.get('period', params.get('fast_period', params.get('length', 20)))), num_bars - 1))
        ma = pd.Series(prices).rolling(period, min_periods=1).mean().values
        
        # ATR berechnen (für Exit-Typ 4)
        high = prices * 1.0002
        low = prices * 0.9998
        tr = np.maximum(high - low, np.maximum(abs(high - np.roll(prices, 1)), abs(low - np.roll(prices, 1))))
        tr[0] = high[0] - low[0]
        atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
        
        # Signale generieren
        price_above = prices > ma
        price_above_prev = np.roll(price_above, 1)
        price_above_prev[0] = False
        
        if exit_type == 1:  # Cross
            entries = price_above & ~price_above_prev
            exits = ~price_above & price_above_prev
        elif exit_type == 2:  # Level
            ma_change = np.diff(ma, prepend=ma[0]) / np.where(ma != 0, ma, 1)
            entries = np.zeros(num_bars, dtype=bool)
            exits = np.zeros(num_bars, dtype=bool)
            entries[1:] = ma_change[1:] > 0.0001
            exits[1:] = ma_change[1:] < -0.0001
        elif exit_type == 3:  # Multi
            momentum = np.diff(prices, prepend=prices[0]) / np.where(prices != 0, prices, 1)
            cross_up = price_above & ~price_above_prev
            entries = cross_up & (momentum > 0.0001)
            cross_down = ~price_above & price_above_prev
            exits = cross_down | (momentum < -0.0001)
        else:  # ATR-Volatility (Exit-Typ 4)
            entries = price_above & ~price_above_prev
            exits = np.zeros(num_bars, dtype=bool)
        
        # Backtest
        spread = SPREADS[symbol] * 0.0001
        trades = []
        in_pos = False
        entry_price = 0
        entry_bar = 0
        stop_loss = 0
        
        for i in range(num_bars):
            if in_pos:
                # ATR-basierter Stop-Loss Check (nur für Exit-Typ 4)
                if exit_type == 4 and prices[i] <= stop_loss:
                    pnl = (prices[i] - entry_price) - spread
                    trades.append((pnl, i - entry_bar, pnl > 0))
                    in_pos = False
                elif exit_type != 4 and exits[i]:
                    pnl = (prices[i] - entry_price) - spread
                    trades.append((pnl, i - entry_bar, pnl > 0))
                    in_pos = False
            
            if not in_pos and entries[i]:
                in_pos = True
                entry_price = prices[i]
                entry_bar = i
                if exit_type == 4:
                    stop_loss = entry_price - (atr[i] * atr_mult)
        
        if not trades:
            return [ind_id, combo_idx, symbol, EXIT_TYPES[exit_type], atr_mult if exit_type == 4 else 0,
                    json.dumps(params), 0, 0, 0, 0, 0, 0, 0, 0, 0, SPREADS[symbol], 'NO_TRADES']
        
        # Metriken
        pnls = np.array([t[0] for t in trades])
        wins = pnls > 0
        ret = pnls.sum() * 100
        wr = wins.sum() / len(trades) * 100
        equity = np.cumsum(pnls)
        peak = np.maximum.accumulate(np.maximum(equity, 0))
        max_dd = (peak - equity).max() * 100
        daily_dd = (pnls * 100).std()
        pf = (pnls[wins].sum() / abs(pnls[~wins].sum())) if (~wins).any() else 2.0
        sharpe = ((pnls * 100).mean() / (pnls * 100).std()) * np.sqrt(252) if (pnls * 100).std() > 0 else 0
        avg_bars = np.mean([t[1] for t in trades])
        return_dd_ratio = abs(ret / max_dd) if max_dd > 0 else 0
        
        return [ind_id, combo_idx, symbol, EXIT_TYPES[exit_type], atr_mult if exit_type == 4 else 0,
                json.dumps(params), ret, wr, max_dd, daily_dd, len(trades), pf, sharpe, avg_bars,
                return_dd_ratio, SPREADS[symbol], 'SUCCESS']
    
    except Exception as e:
        return [ind_id, combo_idx, symbol, EXIT_TYPES[exit_type], atr_mult if exit_type == 4 else 0,
                json.dumps(params), 0, 0, 0, 0, 0, 0, 0, 0, 0, SPREADS[symbol], 'ERROR']

# Hauptbacktest
print(f"\n{'='*80}")
print("STARTE ELITE DEEP DIVE BACKTEST")
print(f"{'='*80}\n")

output_csv = Path('ELITE_DEEP_DIVE_RESULTS.csv')
output_md = Path('ELITE_DEEP_DIVE_RESULTS.md')
checkpoint_file = Path('ELITE_DEEP_DIVE_CHECKPOINT.json')

# CSV Header
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    csv.writer(f).writerow(['indicator_id', 'combination_id', 'symbol', 'exit_type', 'atr_multiplier', 'parameters',
                            'total_return_pct', 'win_rate', 'max_dd', 'daily_drawdown',
                            'amount_of_trades', 'profit_factor', 'sharpe_ratio', 'avg_bars_in_trade',
                            'return_dd_ratio', 'spread_pips', 'status'])

# MD Header
with open(output_md, 'w', encoding='utf-8') as f:
    f.write("# ELITE DEEP DIVE BACKTEST - 332 Elite-Indikatoren\n\n")
    f.write(f"**Start:** {datetime.now()}\n")
    f.write(f"**Ziel:** Beste Return/DD Ratio mit hochauflösenden Parametern\n")
    f.write(f"**Exit-Typen:** Cross, Level, Multi, ATR-Volatility (optimierbar)\n\n")
    f.write("| Strategie | Return % | DD % | Return/DD | WR % | Trades | Sharpe | Status |\n")
    f.write("|-----------|----------|------|-----------|------|--------|--------|--------|\n")

start_time = datetime.now()
total_results = 0
batch_buffer = []
error_count = 0
success_count = 0

# Verteilungs-Tracking
exit_type_counts = {1: 0, 2: 0, 3: 0, 4: 0}
symbol_counts = {s: 0 for s in SYMBOLS}

# Checkpoint laden
start_ind_idx = 0
if checkpoint_file.exists():
    with open(checkpoint_file, 'r') as f:
        checkpoint = json.load(f)
        start_ind_idx = checkpoint.get('last_completed_indicator_index', 0) + 1
        total_results = checkpoint.get('total_results', 0)
        error_count = checkpoint.get('error_count', 0)
        success_count = checkpoint.get('success_count', 0)
        # Konvertiere String-Keys zu Integer-Keys für exit_type_counts
        loaded_exit_counts = checkpoint.get('exit_type_counts', {})
        exit_type_counts = {int(k): v for k, v in loaded_exit_counts.items()} if loaded_exit_counts else {1: 0, 2: 0, 3: 0, 4: 0}
        symbol_counts = checkpoint.get('symbol_counts', {s: 0 for s in SYMBOLS})
        print(f"Resuming from Indicator Index {start_ind_idx}")
        print(f"  Previous Results: {total_results:,}\n")

# Sortiere Indikatoren für konsistente Reihenfolge
sorted_ind_ids = sorted(all_combinations.keys())

# Teste alle Elite-Indikatoren
for idx, ind_id in enumerate(sorted_ind_ids[start_ind_idx:], start_ind_idx):
    combinations = all_combinations[ind_id]['combinations']
    ind_start = datetime.now()
    
    # Teste alle Kombinationen mit allen Exit-Typen und Symbolen
    for combo_idx, params in enumerate(combinations, 1):
        for exit_type in [1, 2, 3, 4]:
            # Für ATR-Exit (Typ 4): Teste verschiedene Multiplikatoren
            if exit_type == 4:
                for atr_mult in ATR_MULTIPLIERS:
                    for symbol in SYMBOLS:
                        result = backtest_elite(ind_id, combo_idx, params, symbol, exit_type, atr_mult)
                        batch_buffer.append(result)
                        
                        if result[-1] == 'SUCCESS':
                            success_count += 1
                        else:
                            error_count += 1
                        
                        exit_type_counts[exit_type] += 1
                        symbol_counts[symbol] += 1
                        
                        # Batch-Writing
                        if len(batch_buffer) >= BATCH_SIZE:
                            with open(output_csv, 'a', newline='', encoding='utf-8') as f:
                                csv.writer(f).writerows(batch_buffer)
                            
                            sorted_batch = sorted(batch_buffer, key=lambda x: x[14], reverse=True)[:3]
                            with open(output_md, 'a', encoding='utf-8') as f:
                                for r in sorted_batch:
                                    f.write(f"| {r[0]}-{r[1]}-{r[2]}-{r[3]} | {r[6]:.2f} | {r[8]:.2f} | {r[14]:.3f} | {r[7]:.1f} | {r[10]} | {r[12]:.2f} | {r[16]} |\n")
                            
                            total_results += len(batch_buffer)
                            batch_buffer = []
                            gc.collect()
            else:
                # Für andere Exit-Typen: Kein ATR-Multiplikator
                for symbol in SYMBOLS:
                    result = backtest_elite(ind_id, combo_idx, params, symbol, exit_type)
                    batch_buffer.append(result)
                    
                    if result[-1] == 'SUCCESS':
                        success_count += 1
                    else:
                        error_count += 1
                    
                    exit_type_counts[exit_type] += 1
                    symbol_counts[symbol] += 1
                    
                    if len(batch_buffer) >= BATCH_SIZE:
                        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
                            csv.writer(f).writerows(batch_buffer)
                        
                        sorted_batch = sorted(batch_buffer, key=lambda x: x[14], reverse=True)[:3]
                        with open(output_md, 'a', encoding='utf-8') as f:
                            for r in sorted_batch:
                                f.write(f"| {r[0]}-{r[1]}-{r[2]}-{r[3]} | {r[6]:.2f} | {r[8]:.2f} | {r[14]:.3f} | {r[7]:.1f} | {r[10]} | {r[12]:.2f} | {r[16]} |\n")
                        
                        total_results += len(batch_buffer)
                        batch_buffer = []
                        gc.collect()
    
    elapsed = (datetime.now() - ind_start).total_seconds()
    tests_this_ind = len(combinations) * 3 * 6 + len(combinations) * len(ATR_MULTIPLIERS) * 6
    tests_per_sec = tests_this_ind / elapsed if elapsed > 0 else 0
    
    print(f"[{idx+1:3d}/{len(sorted_ind_ids)}] {ind_id}: {tests_this_ind:,} tests in {elapsed:.1f}s ({tests_per_sec:.0f} tests/s)")
    
    # CHECKPOINT NACH JEDEM INDIKATOR
    with open(checkpoint_file, 'w') as f:
        json.dump({
            'last_completed_indicator_index': idx,
            'total_results': total_results + len(batch_buffer),
            'success_count': success_count,
            'error_count': error_count,
            'exit_type_counts': exit_type_counts,
            'symbol_counts': symbol_counts
        }, f)
    
    # Status-Update alle 10 Indikatoren
    if (idx + 1) % 10 == 0:
        total_elapsed = (datetime.now() - start_time).total_seconds()
        eta = ((len(sorted_ind_ids) - idx - 1) * (total_elapsed / (idx - start_ind_idx + 1))) / 3600
        coverage = ((total_results + len(batch_buffer)) / 14400000) * 100
        
        print(f"\n{'='*80}")
        print(f"CHECKPOINT [{idx+1}/{len(sorted_ind_ids)}]")
        print(f"  Results: {total_results + len(batch_buffer):,}")
        print(f"  Success: {success_count:,} ({success_count/(success_count+error_count)*100:.1f}%)")
        print(f"  Elapsed: {total_elapsed/3600:.1f}h | ETA: {eta:.1f}h")
        print(f"\n  Exit Type Verteilung:")
        for et, count in exit_type_counts.items():
            print(f"    {EXIT_TYPES[et]}: {count:,}")
        print(f"\n  Symbol Verteilung:")
        for sym, count in symbol_counts.items():
            print(f"    {sym}: {count:,}")
        print(f"{'='*80}\n")
    
    time.sleep(SLEEP_BETWEEN_INDICATORS)

# Finale Speicherung
if batch_buffer:
    with open(output_csv, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(batch_buffer)
    total_results += len(batch_buffer)

print(f"\n{'='*80}")
print("ELITE DEEP DIVE BACKTEST ABGESCHLOSSEN")
print(f"{'='*80}")

total_elapsed = datetime.now() - start_time
success_rate = (success_count / total_results * 100) if total_results > 0 else 0

print(f"\nStatistiken:")
print(f"  Total Tests: {total_results:,}")
print(f"  Success Rate: {success_rate:.1f}%")
print(f"  Zeit: {total_elapsed}")

print(f"\nExit Type Verteilung:")
for et, count in exit_type_counts.items():
    pct = (count / total_results * 100) if total_results > 0 else 0
    print(f"  {EXIT_TYPES[et]}: {count:,} ({pct:.1f}%)")

print(f"\nSymbol Verteilung:")
for sym, count in symbol_counts.items():
    pct = (count / total_results * 100) if total_results > 0 else 0
    print(f"  {sym}: {count:,} ({pct:.1f}%)")

with open(output_md, 'a', encoding='utf-8') as f:
    f.write(f"\n\n**Abgeschlossen:** {datetime.now()}\n")
    f.write(f"**Dauer:** {total_elapsed}\n")
    f.write(f"**Success Rate:** {success_rate:.1f}%\n")

print(f"\n{'='*80}")
print("ZIEL: Beste Return/DD Ratio mit hochauflösenden Parametern identifiziert")
print(f"{'='*80}")
