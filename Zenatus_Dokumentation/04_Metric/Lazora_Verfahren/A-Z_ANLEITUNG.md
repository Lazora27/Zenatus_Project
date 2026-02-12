# 🎯 A-Z ANLEITUNG - LAZORA PHASE 1 BACKTEST

---

## 📋 **ÜBERBLICK**

**Was wir haben:**
- 592 Indikatoren (Fixed Exit)
- 6 Symbols (EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD, NZD_USD)
- 4 Timeframes (1H, 30M, 15M, 5M)
- Sobol Sampling (500 intelligente Parameter-Kombinationen)
- Walk-Forward 80/20 (Train/Test Split)
- Checkpoint System (Resume nach Crash)

**Was wir wollen:**
- Beste Strategie PRO SYMBOL PRO TIMEFRAME finden
- Top 1000 Listen (Sharpe Ratio + Profit Factor)
- Heatmaps zur Visualisierung

---

## 🚀 **SCHRITT 1: VORBEREITUNG** ✅

### 1.1 Check Matrix Ranges
```powershell
cd D:\2_Trading\Superindikator_Alpha
python 08_Lazora_Verfahren\01_MATRIX_CALCULATOR.py
```

**Output:**
- `08_Lazora_Verfahren/MATRIX_RANGES_COMPLETE.json` ✅
- `08_Lazora_Verfahren/MATRIX_SUMMARY.csv` ✅

**Was passiert:**
- Berechnet für jeden Indikator: Min/Max Parameter Ranges
- Total Combinations (Entry × Exit)
- Efficiency Ratio (500 samples / total combos)

**Check:**
```
Loaded 592 indicators
Avg Total Combos: ~3.5 Million
Max Combos: 1.6 Billion (StochRSI)
```

---

### 1.2 Erstelle Wörterbuch
```powershell
python 08_Lazora_Verfahren\02_DICTIONARY_GENERATOR.py
```

**Output:**
- `10_Dictionary/INDICATOR_ENCYCLOPEDIA.json` ✅
- `10_Dictionary/INDICATOR_ENCYCLOPEDIA.csv` ✅
- `10_Dictionary/ENCYCLOPEDIA_SUMMARY.txt` ✅

**Was passiert:**
- Erstellt strukturierte Dokumentation für alle 592 Indikatoren
- Mit Default Values, Parameter Types, Matrix Ranges

---

## 🔬 **SCHRITT 2: BACKTEST DURCHFÜHREN**

### 2.1 Test Run (1H - kleinster Timeframe)
```powershell
cd D:\2_Trading\Superindikator_Alpha
python 08_Lazora_Verfahren\LAZORA_PHASE1_1H.py
```

**Runtime:** ~3-6 Stunden (592 Indikatoren × 5min avg)

**Terminal Output:**
```
[15:32:45] Ind#001 | 001_trend_sma | 6 symbols | 45.2s | Best: SR=2.34, PF=1.87, Ret=12.45%, DD=3.21%
[15:33:30] Ind#002 | 002_trend_ema | 6 symbols | 43.8s | Best: SR=1.92, PF=1.54, Ret=8.32%, DD=2.87%
...
```

**Check Progress:**
```powershell
# Schau nach wie viele CSVs bereits erstellt wurden:
ls 01_Backtest_System\Documentation\Fixed_Exit\1h\*.csv | Measure-Object
# Output: Count : 15  <- 15 von 592 fertig
```

**Bei Crash:**
- Script wird automatisch ab letztem gespeicherten Checkpoint fortgesetzt
- Checkpoint File: `01_Backtest_System/CHECKPOINTS/lazora_phase1_1h.json`

---

### 2.2 Check Output

**CSV Resultate:**
```
01_Backtest_System/Documentation/Fixed_Exit/1h/
├── 001_trend_sma.csv  (3 Zeilen pro Combo × 500 samples = ~1500 Zeilen)
├── 002_trend_ema.csv
├── ...
```

**CSV Struktur:**
```
Indicator_Num, Indicator, Symbol, Phase, Combo_Index, TP_Pips, SL_Pips, 
period (oder andere params), Total_Return, Max_Drawdown, Daily_Drawdown,
Win_Rate_%, Total_Trades, Profit_Factor, Sharpe_Ratio
```

**3 Rows pro Combo:**
- Row 1: TRAIN (80% - 2023-01-01 bis 2025-09-20)
- Row 2: TEST (20% - 2025-09-20 bis 2026-01-01)
- Row 3: FULL (100% - 2023-01-01 bis 2026-01-01)

**Heatmap Data:**
```
08_Heatmaps/Fixed_Exit/1h/
├── 001_trend_sma_heatmap_data.csv
├── 002_trend_ema_heatmap_data.csv
├── ...
```

---

### 2.3 Alle Timeframes (Master Run)

**WICHTIG:** Nur starten wenn 1H erfolgreich war!

```powershell
python 08_Lazora_Verfahren\RUN_ALL_LAZORA_PHASE1.py
```

**Runtime:** ~2-3 Tage für alle 4 Timeframes
- 1H:  ~3-6 hours
- 30M: ~6-12 hours
- 15M: ~12-24 hours
- 5M:  ~12-24 hours

**Output nach Complete:**
```
================================================================================
LAZORA PHASE 1 COMPLETE!
================================================================================
End: 2026-01-27 14:23:15

SUMMARY:
  [OK] 1H  : SUCCESS (5.2h)
  [OK] 30M : SUCCESS (9.8h)
  [OK] 15M : SUCCESS (18.4h)
  [OK] 5M  : SUCCESS (22.1h)

================================================================================
Output:
  CSV: 01_Backtest_System/Documentation/Fixed_Exit/[TF]/
  Heatmap Data: 08_Heatmaps/Fixed_Exit/[TF]/
  Checkpoints: 01_Backtest_System/CHECKPOINTS/
================================================================================
```

---

## 📊 **SCHRITT 3: HEATMAPS GENERIEREN**

**Nach Backtest Complete für 1H:**

```powershell
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 1h
```

**Output:**
```
08_Heatmaps/Fixed_Exit/1h/
├── 001_trend_sma_heatmap.png
├── 002_trend_ema_heatmap.png
├── ...
```

**Heatmap Features:**
- 1-2 Params: 2D Scatter
- 3 Params: 3D Scatter
- 4+ Params: t-SNE dimensionality reduction
- Color: Sharpe Ratio (Grün = gut, Rot = schlecht)
- Matrix Info: Min/Max Ranges, Total Combos angezeigt

**Für alle Timeframes:**
```powershell
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 1h
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 30m
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 15m
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 5m
```

---

## 🏆 **SCHRITT 4: TOP 1000 RANKINGS ERSTELLEN**

**Nach Backtest Complete:**

```powershell
python 08_Lazora_Verfahren\04_TOP1000_GENERATOR.py
```

**Was passiert:**
- Liest alle CSV Files aus `Documentation/Fixed_Exit/[TF]/`
- Sortiert nach Sharpe Ratio & Profit Factor
- Erstellt Top 1000 Listen:
  - Pro Symbol (6 × 2 = 12 Files per TF)
  - Gesamt (2 Files per TF)

**Output:**
```
01_Backtest_System/Top_1000_Rankings/1h/
├── EUR_USD_TOP1000_SHARPE.csv
├── EUR_USD_TOP1000_PF.csv
├── GBP_USD_TOP1000_SHARPE.csv
├── GBP_USD_TOP1000_PF.csv
├── ...
├── ALL_SYMBOLS_TOP1000_SHARPE.csv
├── ALL_SYMBOLS_TOP1000_PF.csv
```

**Total Files:**
- 6 Symbols × 2 Metrics × 4 TF = 48
- 2 All-Symbols × 4 TF = 8
- **TOTAL: 56 Files**

**CSV Struktur:**
```
Rank, Indicator_Num, Indicator, Symbol, Phase, Combo_Index, TP_Pips, SL_Pips,
period, Total_Return, Max_Drawdown, Daily_Drawdown, Win_Rate_%, Total_Trades,
Profit_Factor, Sharpe_Ratio
```

---

## 🔍 **SCHRITT 5: ANALYSE**

### 5.1 Check Top Performer

**Open:**
```
01_Backtest_System/Top_1000_Rankings/1h/EUR_USD_TOP1000_SHARPE.csv
```

**Look for:**
- Rank 1-10: Beste Strategien
- Sharpe Ratio > 2.0 (gut)
- Profit Factor > 1.5 (profitabel)
- Total_Return > 10% (interessant)
- Max_Drawdown < 15% (akzeptabel)

**Beispiel Top 1:**
```
Rank: 1
Indicator: 041_trend_rsi
Symbol: EUR_USD
Sharpe_Ratio: 3.45
Profit_Factor: 2.87
Total_Return: 24.32%
Max_Drawdown: 8.71%
```

---

### 5.2 Check Heatmap

**Open:**
```
08_Heatmaps/Fixed_Exit/1h/041_trend_rsi_heatmap.png
```

**Analyse:**
- Grüne Cluster = "Hot Zones" (gute Parameter-Bereiche)
- Rote Bereiche = "Cold Zones" (schlechte Parameter)
- Matrix Info zeigt: Min/Max Ranges, Total Combos

**Für Phase 2 (später):**
- Zoome in auf Grüne Cluster
- Teste dichter in diesen Bereichen (500 neue Samples)

---

### 5.3 Cross-Reference Train vs Test

**Check ob Strategie robust ist:**

**Open CSV:**
```
01_Backtest_System/Documentation/Fixed_Exit/1h/041_trend_rsi.csv
```

**Filter auf Best Combo (z.B. Combo_Index = 234):**
```
Row 1 (TRAIN): Sharpe=3.45, Return=25.2%, DD=8.1%
Row 2 (TEST):  Sharpe=2.89, Return=18.7%, DD=9.2%
Row 3 (FULL):  Sharpe=3.12, Return=22.4%, DD=8.7%
```

**Gut wenn:**
- TEST Sharpe > 2.0 (robust!)
- TEST Return > 15% (profitabel!)
- TRAIN/TEST Gap < 20% (kein Overfitting!)

**Schlecht wenn:**
- TRAIN Sharpe = 5.0, TEST Sharpe = 0.5 (Overfitting!)
- TEST DD > 30% (zu riskant!)

---

## ✅ **SCHRITT 6: WINNER SELECTION**

### 6.1 Kriterien für Winner

**Must Have:**
1. ✅ Sharpe Ratio (TEST) > 1.5
2. ✅ Profit Factor (FULL) > 1.5
3. ✅ Max Drawdown (FULL) < 20%
4. ✅ Total Trades (FULL) > 30
5. ✅ TRAIN/TEST Consistency (Gap < 30%)

**Nice to Have:**
- Daily Drawdown < 10%
- Win Rate > 45%
- Return > 15%

---

### 6.2 Filter Top 1000 Lists

**PowerShell Command:**
```powershell
# Import CSV
$df = Import-Csv "01_Backtest_System\Top_1000_Rankings\1h\EUR_USD_TOP1000_SHARPE.csv"

# Filter Winners
$winners = $df | Where-Object { 
    [double]$_.Sharpe_Ratio -gt 1.5 -and 
    [double]$_.Profit_Factor -gt 1.5 -and 
    [double]$_.Max_Drawdown -lt 20.0 
}

# Count
$winners.Count
```

**Expected:**
- ~50-200 Winners pro Symbol pro TF
- → Total: 50-200 × 6 Symbols × 4 TF = **1200-4800 Winner Strategien**

---

## 🚀 **NÄCHSTE SCHRITTE (FUTURE)**

### Phase 2: Adaptive Refinement (später)
- Hot Zone Detection (Top 20% Sharpe aus Phase 1)
- Denser Sampling (500 neue Samples in Hot Zones)
- → Finde lokale Optima

### Phase 3: Ultra-Fine Tuning (später)
- Top 5 Kandidaten aus Phase 2
- Micro-Grid Search (±5% Range, 300 Samples per Kandidat)
- → Finde globale Optima

### Risk Management (später)
- Kelly Criterion Position Sizing
- Dynamic TP/SL (ATR-based)
- Regime Detection (Volatility, Trend, Range)

### Portfolio Construction (später)
- Correlation Analysis (Low-Corr Strategien kombinieren)
- Diversification (Multi-Symbol, Multi-TF, Multi-Strategy)
- Risk-Parity Allocation

---

## 📁 **ORDNERSTRUKTUR FINAL**

```
D:\2_Trading\Superindikator_Alpha\
│
├── 01_Backtest_System/
│   ├── Documentation/
│   │   ├── Fixed_Exit/
│   │   │   ├── 1h/  (592 CSV files)
│   │   │   ├── 30m/ (592 CSV files)
│   │   │   ├── 15m/ (592 CSV files)
│   │   │   └── 5m/  (592 CSV files)
│   │   └── ATR_Based_Exit/  (leer, für später)
│   │
│   ├── Top_1000_Rankings/
│   │   ├── 1h/  (14 CSV files)
│   │   ├── 30m/ (14 CSV files)
│   │   ├── 15m/ (14 CSV files)
│   │   └── 5m/  (14 CSV files)
│   │
│   ├── CHECKPOINTS/  (Resume Files)
│   └── LOGS/  (Log Files)
│
├── 08_Lazora_Verfahren/
│   ├── 01_MATRIX_CALCULATOR.py
│   ├── 02_DICTIONARY_GENERATOR.py
│   ├── 03_HEATMAP_VISUALIZER.py
│   ├── 04_TOP1000_GENERATOR.py
│   ├── LAZORA_PHASE1_1H.py
│   ├── LAZORA_PHASE1_30M.py
│   ├── LAZORA_PHASE1_15M.py
│   ├── LAZORA_PHASE1_5M.py
│   ├── RUN_ALL_LAZORA_PHASE1.py
│   ├── MATRIX_RANGES_COMPLETE.json
│   ├── MATRIX_SUMMARY.csv
│   ├── IMPLEMENTATION_STATUS.md
│   └── QUICK_START.md
│
├── 08_Heatmaps/
│   ├── Fixed_Exit/
│   │   ├── 1h/  (592 PNG + 592 CSV)
│   │   ├── 30m/ (592 PNG + 592 CSV)
│   │   ├── 15m/ (592 PNG + 592 CSV)
│   │   └── 5m/  (592 PNG + 592 CSV)
│   └── Dynamic_Exit/  (leer, für später)
│
├── 09_Validation_Methods/
│   ├── Walk_Forward/
│   │   └── README.md
│   └── NIKOLA_NACHSCHAUEN_FUTURE/
│       └── FUTURE_ROBUSTNESS_TESTS.md
│
├── 10_Dictionary/
│   ├── INDICATOR_ENCYCLOPEDIA.json
│   ├── INDICATOR_ENCYCLOPEDIA.csv
│   └── ENCYCLOPEDIA_SUMMARY.txt
│
└── 99_Heute/
    └── HEUTE_SUMMARY.md
```

---

## ⚠️ **TROUBLESHOOTING**

### Problem: Script crashed
**Lösung:** Starte Script erneut → automatischer Resume ab Checkpoint

### Problem: UnicodeEncodeError
**Lösung:** Emoji-Issue im Terminal, kann ignoriert werden (Output files sind OK)

### Problem: Zu wenig RAM
**Lösung:** Reduziere MAX_WORKERS von 6 auf 3 oder 2

### Problem: vectorbt ImportError
**Lösung:** `pip install vectorbt`

### Problem: scipy ImportError
**Lösung:** `pip install scipy scikit-learn matplotlib`

---

## 🎯 **ZUSAMMENFASSUNG**

**Was du jetzt tun kannst:**

1. ✅ **Starte 1H Backtest** (3-6h)
   ```powershell
   python 08_Lazora_Verfahren\LAZORA_PHASE1_1H.py
   ```

2. ✅ **Check Output nach 1h** (10-15 Indikatoren fertig)
   ```powershell
   ls 01_Backtest_System\Documentation\Fixed_Exit\1h\*.csv
   ```

3. ✅ **Wenn OK: Starte Master Run** (2-3 Tage)
   ```powershell
   python 08_Lazora_Verfahren\RUN_ALL_LAZORA_PHASE1.py
   ```

4. ✅ **Nach Complete: Generate Heatmaps & Top 1000**
   ```powershell
   python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 1h
   python 08_Lazora_Verfahren\04_TOP1000_GENERATOR.py
   ```

5. ✅ **Analyse Winners & Start Prop Accounts!** 🚀

---

**READY TO GO!** 🎉
