# 🚀 MULTI-TIMEFRAME PIPELINE - START GUIDE

## 📋 **ÜBERSICHT**

Diese Pipeline analysiert **ALLE 595 Indikatoren** über **4 Timeframes** automatisch:

```
Pipeline Flow:
┌─────────────────────────────────────────────────┐
│  30m → 595 Indikatoren → ~2h   → Run_30m/      │
│  15m → 595 Indikatoren → ~2h   → Run_15m/      │
│  5m  → 595 Indikatoren → ~2.5h → Run_5m/       │
│  1h  → 595 Indikatoren → ~1.5h → Run_1h/       │
├─────────────────────────────────────────────────┤
│  TOTAL: ~8 Stunden                              │
│  OUTPUT: ~1.4 Million Backtest-Resultate        │
└─────────────────────────────────────────────────┘
```

---

## ⚡ **SCHNELLSTART (1 Befehl)**

```bash
cd /opt/Zenatus_Backtester\01_Backtest_System\Scripts
python MULTI_TIMEFRAME_PIPELINE.py
```

**Das war's!** Die Pipeline läuft jetzt automatisch durch alle Timeframes.

---

## 📊 **WAS PASSIERT**

### **Phase 1: Timeframe 30m (2h)**
- Lädt 30m Daten für alle 6 Symbole
- Testet alle 595 Indikatoren
- ~200 TP/SL Kombinationen pro Indikator
- Output: `Multi_TF_Pipeline/Run_XXXXXX/30m/`

### **Phase 2: Timeframe 15m (2h)**
- Automatischer Wechsel nach 30m
- Neue Daten laden
- Komplett unabhängig von Phase 1
- Output: `Multi_TF_Pipeline/Run_XXXXXX/15m/`

### **Phase 3: Timeframe 5m (2.5h)**
- Mehr Bars = etwas länger
- Höhere Frequenz = mehr Trades
- Output: `Multi_TF_Pipeline/Run_XXXXXX/5m/`

### **Phase 4: Timeframe 1h (1.5h)**
- Weniger Bars = schneller
- Längerfristige Trades
- Output: `Multi_TF_Pipeline/Run_XXXXXX/1h/`

---

## 📁 **OUTPUT-STRUKTUR**

```
01_Backtest_System/
├── Documentation/
│   └── Multi_TF_Pipeline/
│       └── Run_20260120_223000/
│           ├── 30m/
│           │   ├── 001_trend_sma.csv
│           │   ├── 002_trend_ema.csv
│           │   └── ... (595 CSV files)
│           ├── 15m/
│           │   ├── 001_trend_sma.csv
│           │   └── ... (595 CSV files)
│           ├── 5m/
│           │   └── ... (595 CSV files)
│           ├── 1h/
│           │   └── ... (595 CSV files)
│           └── PIPELINE_SUMMARY.csv
└── LOGS/
    ├── PIPELINE_20260120_223000.log (Master)
    ├── TF_30m_20260120_223000.log
    ├── TF_15m_20260120_223000.log
    ├── TF_5m_20260120_223000.log
    └── TF_1h_20260120_223000.log
```

---

## 🔍 **FORTSCHRITT ÜBERWACHEN**

### **Option 1: Master Log (Empfohlen)**
```powershell
Get-Content "/opt/Zenatus_Backtester\01_Backtest_System\LOGS\PIPELINE_*.log" -Wait -Tail 20
```

### **Option 2: Aktuelles Timeframe**
```powershell
# Während 30m läuft:
Get-Content "/opt/Zenatus_Backtester\01_Backtest_System\LOGS\TF_30m_*.log" -Wait -Tail 20
```

---

## 📈 **ERWARTETE PERFORMANCE**

| Timeframe | Bars (2024) | Zeit | Tests/s | Results |
|-----------|-------------|------|---------|---------|
| **30m** | ~21,000 | 2.0h | 180 | ~350k |
| **15m** | ~42,000 | 2.0h | 180 | ~350k |
| **5m** | ~125,000 | 2.5h | 150 | ~350k |
| **1h** | ~10,500 | 1.5h | 220 | ~350k |

**TOTAL: ~1.4 Million Backtest-Resultate!**

---

## 🎯 **NACH DER PIPELINE**

### **1. Analysiere PIPELINE_SUMMARY.csv**
```python
import pandas as pd

summary = pd.read_csv('PIPELINE_SUMMARY.csv')
print(summary)

# Output:
#   timeframe    time  indicators  results     rate
# 0       30m  7200.5         595   352000    180.2
# 1       15m  7100.2         595   348000    182.1
# 2        5m  9000.8         595   355000    147.3
# 3        1h  5400.3         595   345000    223.4
```

### **2. Identifiziere Top-Performer**
```python
# Lade alle Results
df_30m = pd.read_csv('30m/001_trend_sma.csv')
df_15m = pd.read_csv('15m/001_trend_sma.csv')
# ...

# Finde beste Timeframe für jeden Indikator
best_tf = df.groupby('Indicator')['Profit_Factor'].max()
```

### **3. Cross-Timeframe Analyse**
- Welche Indikatoren funktionieren auf ALLEN Timeframes?
- Welche Timeframe hat die besten Profit Factors?
- Korrelation zwischen Timeframes?

---

## ⚙️ **KONFIGURATION ANPASSEN**

Öffne `MULTI_TIMEFRAME_PIPELINE.py`:

### **Andere Timeframes:**
```python
# Zeile 44:
TIMEFRAMES = ['30m', '15m', '5m', '1h']

# Ändern zu z.B.:
TIMEFRAMES = ['1h', '4h', '1d']  # Längerfristig
```

### **Andere Symbole:**
```python
# Zeile 47:
SYMBOLS = ['AUD_USD', 'EUR_USD', 'GBP_USD', 'NZD_USD', 'USD_CAD', 'USD_CHF']

# Hinzufügen:
SYMBOLS = ['AUD_USD', 'EUR_USD', ..., 'GBP_JPY', 'EUR_GBP']
```

### **Mehr/Weniger Kombinationen:**
```python
# Zeile 50:
COMBINATIONS = 200

# Ändern zu:
COMBINATIONS = 500  # Mehr Genauigkeit
```

---

## 🚨 **WICHTIG**

### **Während Pipeline läuft:**
- ✅ Computer muss AN bleiben
- ✅ Python-Prozess nicht unterbrechen
- ✅ Genug Festplatten-Speicher (~5GB Output)
- ✅ Keine anderen schweren Programme

### **Bei Unterbrechung:**
- Jedes Timeframe ist unabhängig
- Bereits fertige Timeframes bleiben erhalten
- Einfach neu starten (überspringt keine Daten)

---

## 💡 **OPTIMIERUNGS-TIPPS**

### **Schneller:**
```python
# Weniger Kombinationen
COMBINATIONS = 100

# Nur schnelle Indikatoren (z.B. erste 100)
indicators = indicators[:100]
```

### **Genauer:**
```python
# Mehr Kombinationen
COMBINATIONS = 500

# Kleinerer Early Stop
if trades < 10:  # Statt 5
    return None
```

---

## 🎉 **VISION ERFÜLLT**

```
Von 242 Tagen auf 8 Stunden!
Systematische Analyse aller Timeframes!
Identifikation der profitabelsten Strategien!
Grundlage für Prop-Firm Trading!
```

**NEXT LEVEL UNLOCKED!** 🚀

---

**Author:** Nikola Cekic  
**Date:** 2026-01-20  
**Purpose:** Systematische Multi-Timeframe Analyse für optimale Trading-Strategien
