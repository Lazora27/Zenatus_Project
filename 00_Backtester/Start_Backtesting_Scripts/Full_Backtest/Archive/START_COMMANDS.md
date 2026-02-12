# 🚀 QUICK START - COPY & PASTE COMMANDS
========================================

## ✅ BEREIT ZUM STARTEN!

Alle Scripts sind fertig und liegen in:
`/opt/Zenatus_Backtester\01_Backtest_System\Scripts\`

---

## 🎯 OPTION 1: EINZELNE TESTS (Empfohlen für erste Validierung)

### **Start mit 1H (schnellster Test ~5-8min):**
```powershell
python 01_Backtest_System\Scripts\QUICK_TEST_1H_PRODUCTION.py
```

### **Alle anderen Timeframes:**
```powershell
python 01_Backtest_System\Scripts\QUICK_TEST_30M_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_15M_PRODUCTION.py
python 01_Backtest_System\Scripts\QUICK_TEST_5M_PRODUCTION.py
```

---

## 🚀 OPTION 2: ALLE 4 TESTS AUTOMATISCH (Python Master Script)

```powershell
python 01_Backtest_System\Scripts\RUN_ALL_QUICK_TESTS.py
```

**Was passiert:**
- Führt alle 4 Timeframes nacheinander aus (1H → 30M → 15M → 5M)
- Zeigt Fortschritt live im Terminal
- Gibt am Ende Summary mit Success/Fail Status
- Total Zeit: ~30-45min

---

## 💪 OPTION 3: ALLE 4 TESTS AUTOMATISCH (PowerShell Script)

```powershell
.\01_Backtest_System\Scripts\RUN_ALL_QUICK_TESTS.ps1
```

**Falls Execution Policy Error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\01_Backtest_System\Scripts\RUN_ALL_QUICK_TESTS.ps1
```

---

## 📊 WAS WIRD GETESTET:

| Timeframe | TP/SL | Indicators | Date Range | Expected Time |
|-----------|-------|------------|------------|---------------|
| 1H        | 50/25 | 595        | 01.01-01.06.2024 | 5-8 min |
| 30M       | 40/20 | 595        | 01.01-01.06.2024 | 6-10 min |
| 15M       | 30/15 | 595        | 01.01-01.06.2024 | 8-12 min |
| 5M        | 20/10 | 595        | 01.01-01.06.2024 | 10-15 min |

**Mit FTMO Spreads + Slippage + Commission!**

---

## 📂 OUTPUT LOCATION:

Nach jedem Test findest du die Ergebnisse hier:
```
01_Backtest_System/Documentation/Quick_Test/
├── 1h/QUICK_TEST_EUR_USD_20240101_20240601_TIMESTAMP.csv
├── 30m/QUICK_TEST_EUR_USD_20240101_20240601_TIMESTAMP.csv
├── 15m/QUICK_TEST_EUR_USD_20240101_20240601_TIMESTAMP.csv
└── 5m/QUICK_TEST_EUR_USD_20240101_20240601_TIMESTAMP.csv
```

---

## 🔥 EMPFEHLUNG:

### **Schritt 1: Start mit 1H Test**
```powershell
python 01_Backtest_System\Scripts\QUICK_TEST_1H_PRODUCTION.py
```

### **Schritt 2: Ergebnisse checken**
- Öffne CSV in Excel/Notepad++
- Check TOP 10 Return %
- Check Avg Return (sollte zwischen -0.05% und +0.10% sein)
- Wenn meiste Returns NEGATIV → Spreads zu hoch (normal!)

### **Schritt 3: Entscheiden**
- **Wenn 1H gut läuft** → Starte alle anderen Tests
- **Wenn 1H schlecht** → Eventuell Features anpassen

---

## ⚠️ TROUBLESHOOTING:

### **FileNotFoundError:**
```powershell
# Du bist im falschen Verzeichnis! Wechsle zu:
cd /opt/Zenatus_Backtester
# Dann nochmal versuchen
```

### **vectorbt not found:**
```powershell
pip install vectorbt
```

### **No data found:**
```powershell
# Check ob Daten existieren:
ls 00_Core\Market_Data\Market_Data\1h\EUR_USD\EUR_USD_aggregated.csv
```

### **Spreads not found:**
```powershell
# Check ob Spreads existieren:
ls 12_Spreads\FTMO_SPREADS_FOREX.csv
```

---

## 🎯 READY? COPY & PASTE:

```powershell
# 1H Quick Test starten (5-8min):
python 01_Backtest_System\Scripts\QUICK_TEST_1H_PRODUCTION.py
```

**ODER**

```powershell
# Alle 4 Tests automatisch (30-45min):
python 01_Backtest_System\Scripts\RUN_ALL_QUICK_TESTS.py
```

---

## 📧 NACH DEM TEST:

1. Check die CSV Files
2. Analysiere TOP 10 Performers
3. Vergleiche über alle Timeframes
4. Entscheide ob Full Backtest sinnvoll ist

**Bei Fragen: Check `QUICK_START_GUIDE.md`**
