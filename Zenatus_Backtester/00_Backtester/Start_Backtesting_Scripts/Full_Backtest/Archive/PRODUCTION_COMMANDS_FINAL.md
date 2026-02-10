# 🚀 PRODUCTION BACKTEST - FINAL COMMANDS
=========================================

## ✅ **ALLE FEATURES IMPLEMENTIERT:**

### **1. Parameter Optimization ✅**
- Fibonacci-based Period Values: [8, 13, 21, 34, 55, 89]
- Smart TP/SL Combinations: 20-110 TP × 10-55 SL
- Best combo selected by **HIGHEST SHARPE RATIO**

### **2. Walk-Forward 80/20 ✅**
- **Training:** 01.01.2023 - 20.09.2025 (80%)
- **Testing:** 20.09.2025 - 01.01.2026 (20%)
- **3 Sets Metrics:**
  - Train_Return, Train_DD, Train_Daily_DD, Train_WR, Train_Trades, Train_Sharpe, Train_PF
  - Test_Return, Test_DD, Test_Daily_DD, Test_WR, Test_Trades, Test_Sharpe, Test_PF
  - Full_Return, Full_DD, Full_Daily_DD, Full_WR, Full_Trades, Full_Sharpe, Full_PF

### **3. Checkpoint System ✅**
- Saves after **EVERY indicator**
- Resume bei Crash/Abort
- Checkpoint File: `01_Backtest_System/CHECKPOINTS/checkpoint_[TF].json`
- Script kann 10x abgebrochen werden → findet immer Fortsetzung

### **4. Live Terminal Output ✅**
```
[HH:MM:SS] Ind#123 | indicator_name | EUR_USD | Period21 | Combo 45/190 (23.7%) | 15.3s
[DONE] Ind#123 | indicator_name | 6 symbols | 45.2s
```

### **5. Timeouts (Sleep per Indicator) ✅**
- 1H: 5min (300s)
- 30M: 10min (600s)
- 15M: 20min (1200s)
- 5M: 20min (1200s)

### **6. Execution Order ✅**
- **1H → 30M → 15M → 5M** (Highest to Lowest)

### **7. Best Combo per Symbol ✅**
- Für jede Strategie × Symbol: Sharpe, Profit Factor, Return%, DD%
- Der **BESTEN Kombination** (highest Sharpe)

---

## 📋 **START COMMANDS:**

### **🎯 EINZELNE TIMEFRAMES:**

```powershell
# 1H (5min timeout per indicator):
python 01_Backtest_System\Scripts\PRODUCTION_1H_FINAL.py

# 30M (10min timeout per indicator):
python 01_Backtest_System\Scripts\PRODUCTION_30M_FINAL.py

# 15M (20min timeout per indicator):
python 01_Backtest_System\Scripts\PRODUCTION_15M_FINAL.py

# 5M (20min timeout per indicator):
python 01_Backtest_System\Scripts\PRODUCTION_5M_FINAL.py
```

### **🚀 ALLE 4 TIMEFRAMES (Reihenfolge: 1H→30M→15M→5M):**

```powershell
python 01_Backtest_System\Scripts\RUN_ALL_PRODUCTION.py
```

---

## 💾 **CHECKPOINT RESUME:**

Bei Crash/Abort:
1. Einfach Script nochmal starten:
   ```powershell
   python 01_Backtest_System\Scripts\PRODUCTION_1H_FINAL.py
   ```
2. Script liest Checkpoint
3. Überspringt bereits getestete Indikatoren
4. Fährt an letzter Stelle fort

**Checkpoint löschen (Neustart von 0):**
```powershell
Remove-Item 01_Backtest_System\CHECKPOINTS\checkpoint_1h.json
```

---

## 📊 **CSV OUTPUT:**

### **Columns:**
```
Indicator_Num, Indicator, Symbol, Timeframe,
Period, TP_Pips, SL_Pips, Spread_Pips, Slippage_Pips,

# TRAIN (80%)
Train_Return, Train_DD, Train_Daily_DD, Train_WR, Train_Trades,
Train_Sharpe, Train_PF,

# TEST (20%)
Test_Return, Test_DD, Test_Daily_DD, Test_WR, Test_Trades,
Test_Sharpe, Test_PF,

# FULL (100%)
Full_Return, Full_DD, Full_Daily_DD, Full_WR, Full_Trades,
Full_Sharpe, Full_PF
```

### **Location:**
```
01_Backtest_System/Documentation/Fixed_Exit/
├── 1h/PRODUCTION_20230101_20260101_*.csv
├── 30m/PRODUCTION_20230101_20260101_*.csv
├── 15m/PRODUCTION_20230101_20260101_*.csv
└── 5m/PRODUCTION_20230101_20260101_*.csv
```

---

## ⚠️ **WICHTIGE UNTERSCHIEDE ZU VORHER:**

### **WAS IST NEU:**
1. ✅ **Parameter Optimization:** Period wird optimiert (Fibonacci)
2. ✅ **Walk-Forward:** 80/20 Split mit 3 Sets Metriken
3. ✅ **Checkpoint:** Resume bei Crash
4. ✅ **Live Progress:** Echtzeit Terminal Output
5. ✅ **Best Combo:** Nur beste Combo pro Symbol (Sharpe)
6. ✅ **Timeouts:** 5/10/20/20min statt 1min
7. ✅ **Execution Order:** 1H→30M→15M→5M

### **WAS IST GLEICH:**
- ✅ FTMO Spreads + Slippage + Commission
- ✅ vectorbt Engine (validated)
- ✅ Daily Drawdown (equity-based)
- ✅ Sharpe Ratio (freq korrekt)
- ✅ Scientific Notation Prevention

---

## 🎯 **EMPFEHLUNG:**

### **Start mit 1H:**
```powershell
python 01_Backtest_System\Scripts\PRODUCTION_1H_FINAL.py
```

**Warum:**
- Schnellster TF (5min timeout)
- Quick Test zeigte +0.19% avg (profitabel)
- Test Parameter Optimization zuerst

**Dann:**
- Check Output CSV
- Wenn gut → Starte 30M, 15M, 5M
- Wenn schlecht → Analyse/Anpassung

---

## 🚀 **BEREIT? COPY & PASTE:**

```powershell
# Start 1H Production Backtest:
python 01_Backtest_System\Scripts\PRODUCTION_1H_FINAL.py
```

**Terminal Output:**
```
[HH:MM:SS] Ind#123 | indicator_name | 6 symbols | 45.2s | Best: SR=2.34, PF=1.87, Ret=12.45%, DD=3.21%
```

**CSV Dokumentation:**
- Gespeichert unter: `Documentation/Fixed_Exit/1h/123_indicator_name.csv`
- 3 Zeilen pro Kombination (TRAIN, TEST, FULL)
- 200 Kombos × 6 Symbole × 3 Phasen = ~3600 Zeilen pro Indikator

**Bei Crash:**
- Einfach nochmal starten (Resume via Checkpoint)

**ALLES KORREKT UMGESETZT! 🚗✅**
