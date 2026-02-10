# 🚀 QUICK START GUIDE - PRODUCTION BACKTESTS
==============================================

## ❌ PROBLEM:
```
FileNotFoundError: QUICK_TEST_1H_PRODUCTION.py not found
```

**GRUND:** Scripts sind in `01_Backtest_System/Scripts/` aber du startest vom Root.

---

## ✅ LÖSUNG:

### **Option 1: Mit vollem Pfad starten** (Empfohlen!)
```powershell
# Von Root aus (/opt/Zenatus_Backtester):
python 01_Backtest_System\Scripts\QUICK_TEST_1H_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_30M_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_15M_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_5M_PRODUCTION.py
```

### **Option 2: In Scripts-Ordner wechseln**
```powershell
cd 01_Backtest_System\Scripts
python QUICK_TEST_1H_PRODUCTION.py
python QUICK_TEST_30M_PRODUCTION.py
python QUICK_TEST_15M_PRODUCTION.py
python QUICK_TEST_5M_PRODUCTION.py
```

---

## 🎯 EMPFOHLENE REIHENFOLGE:

### **Start mit 1H (schnellster Test):**
```powershell
python 01_Backtest_System\Scripts\QUICK_TEST_1H_PRODUCTION.py
```

**Erwartete Ausgabe:**
```
QUICK TEST - 1H | EUR_USD | 50/25
Spread: 1.0 pips | Slippage: 0.5 pips

[1/595] 001_trend_sma: SUCCESS
[2/595] 002_trend_ema: SUCCESS
...
[595/595] 595_xxx: SUCCESS

250/595 | 8.5min
Saved: 01_Backtest_System/Documentation/Quick_Test/1h/QUICK_TEST_EUR_USD_20240101_20240601_*.csv
```

### **Dann 30M, 15M, 5M:**
```powershell
python 01_Backtest_System\Scripts\QUICK_TEST_30M_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_15M_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_5M_PRODUCTION.py
```

---

## 📊 OUTPUT:

Nach jedem Test:
```
01_Backtest_System/Documentation/Quick_Test/
├── 1h/QUICK_TEST_EUR_USD_20240101_20240601_*.csv
├── 30m/QUICK_TEST_EUR_USD_20240101_20240601_*.csv
├── 15m/QUICK_TEST_EUR_USD_20240101_20240601_*.csv
└── 5m/QUICK_TEST_EUR_USD_20240101_20240601_*.csv
```

---

## ⏱️ ERWARTETE LAUFZEITEN:

| Script | Erwartete Zeit | Erfolgsrate |
|--------|---------------|-------------|
| 1H     | 5-8 min       | ~45-50%     |
| 30M    | 6-10 min      | ~42-48%     |
| 15M    | 8-12 min      | ~40-45%     |
| 5M     | 10-15 min     | ~35-42%     |

**Total: ~30-45 Minuten für alle 4**

---

## 🔧 FEATURES IN QUICK TESTS:

✅ **FTMO Spreads** (EUR/USD = 1.0 pips)
✅ **Slippage** (0.5 pips)
✅ **Commission** ($3/lot)
✅ **Leverage** 1:10
✅ **Position Size** $100 fixed
✅ **Multithreading** (5 workers)
✅ **Timeout** (30s per indicator)
✅ **Date Range** 01.01.2024 - 01.06.2024

---

## 📋 CSV COLUMNS:

```
Indicator_Num, Indicator, Symbol, Timeframe, Status,
TP_Pips, SL_Pips, Spread_Pips, Slippage_Pips,
Total_Return, Max_Drawdown, Daily_Drawdown,
Win_Rate_%, Total_Trades, Winning_Trades, Losing_Trades,
Gross_Profit, Commission, Net_Profit,
Profit_Factor, Sharpe_Ratio, Risk_Reward
```

---

## ⚠️ WICHTIG:

### **Nach dem 1H Quick Test:**
1. CSV öffnen und TOP 10 checken
2. Wenn Return < 0% → Spreads/Slippage zu hoch
3. Wenn Return > 0% → Weiter mit anderen Timeframes

### **Wenn Fehler auftreten:**
- Check dass vectorbt installiert ist: `pip list | findstr vectorbt`
- Check dass Daten vorhanden: `ls 00_Core\Market_Data\Market_Data\1h\EUR_USD\`
- Check dass Spreads vorhanden: `ls 12_Spreads\FTMO_SPREADS_FOREX.csv`

---

## 🚀 READY TO START!

**Kopiere und führe aus:**
```powershell
# 1H Test starten:
python 01_Backtest_System\Scripts\QUICK_TEST_1H_PRODUCTION.py
```

**Dann warten und Ergebnisse analysieren!** 🎯
