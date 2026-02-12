# 🚀 FULL BACKTEST - START COMMANDS
===================================

## ✅ **QUICK TEST ANALYSE - RESULTATE:**

### **1H Quick Test (588/595 Success):**
- Avg Return: **0.19%** ✅ POSITIV
- Avg DD: 3.32%
- TOP 1: `377_mutual_information` → **4.49%** Return @ 1.91% DD

### **30M Quick Test (590/595 Success):**
- Avg Return: **-0.68%** ❌ NEGATIV
- Spreads/Slippage zu hoch für 30M

### **✅ FAZIT: ECHTE RESULTATE!**
- Spreads/Slippage/Commission korrekt eingebaut
- 1H am profitabelsten (realistisch)
- Returns klein aber real (0.19% statt 400%)

---

## 🚀 **FULL BACKTEST SPECS:**

### **CONFIGURATION:**
- **TP/SL Combinations:** ~190 (20-115 TP × 10-55 SL)
- **Symbols:** 6 (EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, NZD/USD)
- **Indicators:** 595
- **Date Range:** 01.01.2023 - 01.01.2026 (3 years!)
- **Total Combinations:** 190 × 6 × 595 = **~680,000 tests per timeframe**

### **FEATURES:**
✅ FTMO Spreads (specific per pair)
✅ Slippage (0.5 pips)
✅ Commission ($3/lot)
✅ Leverage 1:10
✅ Position Size $100 fixed
✅ Multithreading (6 workers)
✅ Timeout (60s per combo)
✅ Daily Drawdown (correct calculation)
✅ Sharpe Ratio
✅ Profit Factor

---

## 📊 **ESTIMATED TIMES:**

| Timeframe | Est. Time | Combinations |
|-----------|-----------|-------------|
| 1H        | 40-60h    | ~680,000    |
| 30M       | 50-70h    | ~680,000    |
| 15M       | 60-80h    | ~680,000    |
| 5M        | 70-90h    | ~680,000    |

**⚠️ WARNUNG: Diese Tests laufen 2-3 TAGE pro Timeframe!**

---

## 🎯 **START COMMANDS:**

### **Option 1: START SINGLE TIMEFRAME**

```powershell
# 1H Full Backtest (~40-60 hours):
python 01_Backtest_System\Scripts\FULL_BACKTEST_1H_PRODUCTION.py
```

```powershell
# 30M Full Backtest (~50-70 hours):
python 01_Backtest_System\Scripts\FULL_BACKTEST_30M_PRODUCTION.py
```

```powershell
# 15M Full Backtest (~60-80 hours):
python 01_Backtest_System\Scripts\FULL_BACKTEST_15M_PRODUCTION.py
```

```powershell
# 5M Full Backtest (~70-90 hours):
python 01_Backtest_System\Scripts\FULL_BACKTEST_5M_PRODUCTION.py
```

---

### **Option 2: START ALL 4 TIMEFRAMES SEQUENTIALLY**

```powershell
# Master launcher (~200-300 hours total!):
python 01_Backtest_System\Scripts\RUN_ALL_FULL_BACKTESTS.py
```

---

## 📂 **OUTPUT LOCATION:**

```
01_Backtest_System/Documentation/Fixed_Exit/
├── 1h/FULL_BACKTEST_20230101_20260101_TIMESTAMP.csv
├── 30m/FULL_BACKTEST_20230101_20260101_TIMESTAMP.csv
├── 15m/FULL_BACKTEST_20230101_20260101_TIMESTAMP.csv
└── 5m/FULL_BACKTEST_20230101_20260101_TIMESTAMP.csv
```

---

## ⚠️ **WICHTIGE HINWEISE:**

### **VOR DEM START:**
1. ✅ Check dass genug Speicher frei ist (>50GB)
2. ✅ Check dass PC durchlaufen kann (2-3 Tage!)
3. ✅ Empfehlung: Start mit 1H (am schnellsten)
4. ✅ Überwache die ersten 1-2h ob Errors

### **WÄHREND DEM LAUF:**
- Progress wird alle 1000 Combos geloggt
- Log File: `01_Backtest_System/LOGS/[TF]_FULL_BACKTEST_*.log`
- CSV wird am Ende erstellt
- Bei Crash: Restart script (skipped existing)

---

## 🎯 **EMPFEHLUNG:**

### **Option A: Start nur 1H** ⭐⭐⭐
```powershell
python 01_Backtest_System\Scripts\FULL_BACKTEST_1H_PRODUCTION.py
```
**Grund:** 1H am profitabelsten + schnellsten

### **Option B: Start alle 4**
```powershell
python 01_Backtest_System\Scripts\RUN_ALL_FULL_BACKTESTS.py
```
**Grund:** Wenn PC 8-12 Tage durchlaufen kann

---

## 📋 **CSV COLUMNS:**

```
Indicator_Num, Indicator, Symbol, Timeframe,
TP_Pips, SL_Pips, Spread_Pips, Slippage_Pips,
Status, Total_Return, Max_Drawdown, Daily_Drawdown,
Win_Rate_%, Total_Trades, Winning_Trades, Losing_Trades,
Gross_Profit, Commission, Net_Profit,
Profit_Factor, Sharpe_Ratio, Risk_Reward
```

---

## 🚀 **READY? COPY & PASTE:**

```powershell
# Start 1H Full Backtest (40-60h):
python 01_Backtest_System\Scripts\FULL_BACKTEST_1H_PRODUCTION.py
```

**Dann Geduld haben und warten!** ⏳
