# 🚀 QUICK BACKTESTS - 252 STRATEGIEN

## ✅ **ERSTELLT: 2 SEPARATE QUICK-BACKTEST SCRIPTS**

### **1. QUICKTEST_PROBLEM_102.py**
- **102 Problem-Strategien** (aus alter Problem-Liste)
- Daterange: 01.01.2024 - 01.06.2024 (5 Monate)
- 10 Minuten Sleep zwischen Indikatoren
- Maximale Parallelisierung (6 Workers)
- Detaillierte Log-Führung
- Vereinfachte Parameter (2 Periods, 2 TP/SL Combos)

### **2. QUICKTEST_CLEAN_150.py**
- **150 Clean-Strategien** (nicht in Problem-Liste)
- Daterange: 01.01.2024 - 01.06.2024 (5 Monate)
- 10 Minuten Sleep zwischen Indikatoren
- Maximale Parallelisierung (6 Workers)
- Detaillierte Log-Führung
- Standard Parameter (3 Periods, 3 TP/SL Combos)

---

## 📊 **KONFIGURATION**

### **Gemeinsame Einstellungen:**
- **Daterange:** 01.01.2024 - 01.06.2024
- **Timeframe:** 1h
- **Symbole:** EUR_USD, GBP_USD, AUD_USD, USD_CHF, NZD_USD, USD_CAD (6 total)
- **Workers:** 6 (maximale Parallelisierung)
- **Sleep:** 600s (10 Minuten) zwischen Indikatoren
- **Timeout:** 900s (15 Minuten) pro Indikator
- **Initial Capital:** 10,000
- **Leverage:** 10
- **Position Size:** 100

### **Problem-Strategien (102):**
- **Periods:** [20, 50]
- **TP/SL Combos:** [(100, 50), (150, 75)]
- **Max Combos:** 2 Periods × 2 TP/SL × 6 Symbole = 24 Combos

### **Clean-Strategien (150):**
- **Periods:** [10, 20, 50]
- **TP/SL Combos:** [(50, 30), (100, 50), (150, 75)]
- **Max Combos:** 3 Periods × 3 TP/SL × 6 Symbole = 54 Combos

---

## 🚀 **STARTEN DER TESTS**

### **Option 1: Beide parallel starten (empfohlen)**

**Terminal 1 - Problem-Strategien:**
```powershell
cd C:\Users\nikol\CascadeProjects\Superindikator_Alpha\01_Backtest_System\Scripts
C:\Users\nikol\CascadeProjects\Superindikator_Alpha\Alpha_Superindikator\Scripts\python.exe QUICKTEST_PROBLEM_102.py
```

**Terminal 2 - Clean-Strategien:**
```powershell
cd C:\Users\nikol\CascadeProjects\Superindikator_Alpha\01_Backtest_System\Scripts
C:\Users\nikol\CascadeProjects\Superindikator_Alpha\Alpha_Superindikator\Scripts\python.exe QUICKTEST_CLEAN_150.py
```

### **Option 2: Nacheinander starten**

**Erst Problem-Strategien:**
```powershell
cd C:\Users\nikol\CascadeProjects\Superindikator_Alpha\01_Backtest_System\Scripts
C:\Users\nikol\CascadeProjects\Superindikator_Alpha\Alpha_Superindikator\Scripts\python.exe QUICKTEST_PROBLEM_102.py
```

**Dann Clean-Strategien:**
```powershell
cd C:\Users\nikol\CascadeProjects\Superindikator_Alpha\01_Backtest_System\Scripts
C:\Users\nikol\CascadeProjects\Superindikator_Alpha\Alpha_Superindikator\Scripts\python.exe QUICKTEST_CLEAN_150.py
```

---

## 📝 **LOG-DATEIEN**

### **Automatisch erstellt:**
- `LOGS/quicktest_problem_102_YYYYMMDD_HHMMSS.log`
- `LOGS/quicktest_clean_150_YYYYMMDD_HHMMSS.log`

### **Log-Format:**
```
[2026-02-01 00:00:00] ================================================================================
[2026-02-01 00:00:00] [START] Indikator #008
[2026-02-01 00:00:00] ================================================================================
[2026-02-01 00:00:01] [OK] Indikator #008 geladen
[2026-02-01 00:00:15] [SUCCESS] Ind#008
[2026-02-01 00:00:15]   Ergebnisse: 12
[2026-02-01 00:00:15]   Timeouts: 0
[2026-02-01 00:00:15]   Beste PF: 1.45
[2026-02-01 00:00:15]   Beste SR: 0.87
[2026-02-01 00:00:15]   Symbol: EUR_USD
[2026-02-01 00:00:15]   Period: 20
[2026-02-01 00:00:15]   TP/SL: 100/50
[2026-02-01 00:00:15]   Dauer: 14.3s
[2026-02-01 00:00:15] 
[2026-02-01 00:00:15] [SLEEP] 10 Minuten Pause...
```

---

## 📊 **ERGEBNIS-DATEIEN**

### **Automatisch erstellt:**
- `Scripts/quicktest_problem_102_results_YYYYMMDD_HHMMSS.json`
- `Scripts/quicktest_clean_150_results_YYYYMMDD_HHMMSS.json`

### **JSON-Format:**
```json
{
  "summary": {
    "total": 102,
    "success": 85,
    "error": 5,
    "no_results": 12
  },
  "results": [
    {
      "ind_id": 8,
      "status": "SUCCESS",
      "results_count": 12,
      "timeout_count": 0,
      "best_pf": 1.45,
      "best_sr": 0.87,
      "best_symbol": "EUR_USD",
      "best_period": 20,
      "best_tp_sl": "100/50",
      "duration": 14.3
    }
  ]
}
```

---

## ⏱️ **GESCHÄTZTE DAUER**

### **Problem-Strategien (102):**
- Pro Indikator: ~30-60 Sekunden (24 Combos)
- Sleep: 10 Minuten × 101 = 1,010 Minuten = **~17 Stunden**
- Test-Zeit: 102 × 45s = 4,590s = **~1.3 Stunden**
- **Total: ~18-19 Stunden**

### **Clean-Strategien (150):**
- Pro Indikator: ~60-90 Sekunden (54 Combos)
- Sleep: 10 Minuten × 149 = 1,490 Minuten = **~25 Stunden**
- Test-Zeit: 150 × 75s = 11,250s = **~3.1 Stunden**
- **Total: ~28-29 Stunden**

### **Beide parallel:**
- **Total: ~28-29 Stunden** (längerer Test bestimmt Dauer)

### **Beide nacheinander:**
- **Total: ~47-48 Stunden**

---

## 🎯 **ERWARTETE ERGEBNISSE**

### **Problem-Strategien (102):**
- **SUCCESS:** ~60-70 (60-70%)
- **ERROR:** ~10-15 (10-15%)
- **NO RESULTS:** ~15-25 (15-25%)
- **TIMEOUT:** ~5-10 (5-10%)

### **Clean-Strategien (150):**
- **SUCCESS:** ~120-135 (80-90%)
- **ERROR:** ~5-10 (3-7%)
- **NO RESULTS:** ~5-15 (3-10%)
- **TIMEOUT:** ~0-5 (0-3%)

---

## 📋 **NACH DEM TEST**

### **1. Analysiere Ergebnisse:**
```powershell
# Öffne JSON-Dateien und prüfe Summary
```

### **2. Kategorisiere neu:**
- SUCCESS → Bereit für Haupt-Backtest
- ERROR → Fehler beheben
- NO RESULTS → Parameter anpassen
- TIMEOUT → Optimierung nötig

### **3. Nächste Schritte:**
- Erfolgreiche Strategien in Haupt-Backtest Pipeline
- Fehlerhafte Strategien debuggen
- Timeout-Strategien optimieren

---

## ✅ **BEREIT ZUM STARTEN!**

Beide Scripts sind fertig und konfiguriert. Du kannst sie jetzt starten!

**Empfehlung:** Starte beide parallel in separaten Terminals für maximale Effizienz.
