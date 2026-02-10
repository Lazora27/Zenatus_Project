# 🚀 **PHASE 1 - PRODUCTION RUN GUIDE**

## **📊 SCOPE (FIXIERT):**

- **Symbole:** 6 (EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD, NZD_USD)
- **Exit:** Fixed TP/SL
- **Timeframes:** 1H, 30M, 15M, 5M
- **Indikatoren:** 595
- **Samples:** 200 (Sobol Sequence)
- **Hardware:** 6 Cores / 6 Threads

---

## **✅ PRE-FLIGHT CHECKLIST:**

### **1. SYSTEM BEREIT?**
```powershell
# Check Python Environment
python --version  # Should be 3.9+

# Check vectorbt
python -c "import vectorbt as vbt; print(vbt.__version__)"

# Check Data
ls "D:\2_Trading\Superindikator_Alpha\00_Core\Market_Data\Market_Data\1h"
# Should show 6 symbol folders
```

### **2. CHECKPOINTS LÖSCHEN (FRESH START)?**
```powershell
# Optional: Clear checkpoints for fresh run
Remove-Item "D:\2_Trading\Superindikator_Alpha\01_Backtest_System\CHECKPOINTS\*.json" -Force
```

### **3. ALTE CSVs LÖSCHEN (OPTIONAL)?**
```powershell
# Optional: Clear old results
Remove-Item "D:\2_Trading\Superindikator_Alpha\01_Backtest_System\Documentation\Fixed_Exit\1h\*.csv" -Force
```

---

## **🎯 START COMMANDS:**

### **OPTION A: SINGLE TIMEFRAME (EMPFOHLEN FÜR TEST)**
```powershell
# Start 1H only
python 08_Lazora_Verfahren\LAZORA_PHASE1_1H.py
```

### **OPTION B: ALL TIMEFRAMES (SEQUENTIAL)**
```powershell
# Run all 4 timeframes (1H → 30M → 15M → 5M)
python 08_Lazora_Verfahren\RUN_ALL_LAZORA_PHASE1.py
```

---

## **📈 ERWARTETE OUTPUT:**

### **TERMINAL OUTPUT (PRO INDIKATOR):**
```
[START] Ind#001 | 001_trend_sma | Loading indicator class...
[LOAD] Ind#001 | Module loaded, searching for class...
[SOBOL] Ind#001 | Generated 200 combinations
[PARALLEL] Ind#001 | Starting 6 parallel symbol tests...
  [EUR_USD] Pre-computing signals for 130 unique param sets (from 200 combos)...
  [EUR_USD] 50/130 param sets computed...
  [EUR_USD] Pre-computation done! 130 valid param sets. Building matrix...
  [EUR_USD] Backtesting 200 combos VECTORIZED...
  [EUR_USD] DONE! Best Combo #123: SR=1.45
  [EUR_USD] Testing TOP 20 combos on TEST+FULL...
  [EUR_USD] ⏱️  pre=12.4s | train_pf=0.9s | daily_dd=0.3s | test_full=1.1s | total=14.7s
  [EUR_USD] ✅ COMPLETE! Documented 20 top combos
  ...
[12:34:56] Ind#001 | 001_trend_sma | 6 symbols | 89.2s | Best: SR=1.45, PF=1.87, Ret=34.56%, DD=12.34%
```

### **PROFILING INTERPRETATION:**
```
pre=12.4s       ← Signal-Generierung (generate_signals_fixed)
train_pf=0.9s   ← Vectorized Portfolio Backtest (TRAIN)
daily_dd=0.3s   ← Daily Drawdown Calculation (Top 20)
test_full=1.1s  ← TEST + FULL Backtests (Top 20)
total=14.7s     ← Gesamt-Zeit pro Symbol
```

**BOTTLENECK ANALYSE:**
- Wenn `pre > 80%` → Signal-Generierung ist Bottleneck (normal!)
- Wenn `train_pf > 30%` → vectorbt zu langsam (unwahrscheinlich)
- Wenn `daily_dd > 20%` → Daily DD Berechnung zu langsam (Bug!)
- Wenn `test_full > 40%` → TEST/FULL zu langsam (check pre-compute!)

---

## **📁 OUTPUT FILES:**

### **1. CSV RESULTS (PRO INDIKATOR):**
```
01_Backtest_System/Documentation/Fixed_Exit/1h/001_001_trend_sma.csv
```

**Struktur:**
- 3 Zeilen pro Combo (TRAIN, TEST, FULL)
- Top 20 Combos pro Symbol
- 6 Symbole = 20 × 3 × 6 = **360 Zeilen pro Indikator**

### **2. HEATMAP DATA:**
```
08_Heatmaps/Fixed_Exit/1h/001_001_trend_sma_heatmap_data.csv
```

**Struktur:**
- Alle 200 Combos (TRAIN only)
- 6 Symbole = **~1200 Zeilen pro Indikator**

### **3. CHECKPOINT:**
```
01_Backtest_System/CHECKPOINTS/lazora_phase1_1h.json
```

**Inhalt:**
```json
{
  "completed_indicators": [1, 2, 3, ..., 42]
}
```

---

## **⏱️ ERWARTETE LAUFZEITEN:**

### **PRO INDIKATOR (DURCHSCHNITT):**
```
Schnelle Indikatoren (SMA, EMA):     1-3 Minuten
Mittlere Indikatoren (MACD, RSI):    3-8 Minuten
Langsame Indikatoren (VIDYA, FRAMA): 10-20 Minuten
Sehr langsame Indikatoren:           20-30 Minuten (selten)
```

**WICHTIG:** Die Zeiten variieren stark je nach Indikator-Komplexität!

### **GESAMT-PROGNOSE (REALISTISCH):**
```
1H:  595 Inds × 5-10 min  = 50-100 Stunden
30M: 595 Inds × 8-15 min  = 80-150 Stunden
15M: 595 Inds × 10-20 min = 100-200 Stunden
5M:  595 Inds × 15-30 min = 150-300 Stunden

GESAMT: 380-750 Stunden = 16-31 TAGE (bei 24/7 Lauf)
```

**MIT OPTIMIERUNGEN (nach Profiling & ProcessPool):**
```
Erwartung: 2-3× schneller
→ 5-15 TAGE für alle 4 Timeframes
```

---

## **🔍 MONITORING & DEBUGGING:**

### **1. PROGRESS TRACKING:**
```powershell
# Check current indicator
Get-Content "01_Backtest_System\CHECKPOINTS\lazora_phase1_1h.json"

# Count completed CSVs
(Get-ChildItem "01_Backtest_System\Documentation\Fixed_Exit\1h\*.csv").Count
```

### **2. PERFORMANCE CHECK:**
```powershell
# Check CPU usage
Get-Process python | Select-Object CPU,WorkingSet

# Check RAM
Get-Process python | Select-Object WS -ExpandProperty WS | ForEach-Object {[math]::Round($_/1GB,2)}
```

### **3. ERROR LOGS:**
```powershell
# Check for errors in terminal output
python 08_Lazora_Verfahren\LAZORA_PHASE1_1H.py 2>&1 | Tee-Object -FilePath "backtest_log.txt"
```

---

## **🚨 TROUBLESHOOTING:**

### **PROBLEM: "No valid combos!"**
**Ursache:** Indikator generiert keine Signale
**Lösung:** Normal! Wird übersprungen.

### **PROBLEM: "TIMEOUT"**
**Ursache:** Symbol-Backtest dauert > 5min (300s)
**Lösung:** 
- Timeout wird geloggt: `[TIMEOUT] Ind#XXX | SYMBOL exceeded 300s (5min)`
- Indikator wird für dieses Symbol übersprungen
- Andere Symbole laufen weiter
- Indikator kann später manuell nachgetestet werden

### **PROBLEM: "Memory Error"**
**Ursache:** Zu wenig RAM
**Lösung:** 
```powershell
# Reduce samples temporarily
# In LAZORA_PHASE1_1H.py:
PHASE1_SAMPLES = 100  # Statt 200
```

### **PROBLEM: Sehr langsam (> 5min pro Indikator)**
**Ursache:** Signal-Generierung ist Bottleneck
**Lösung:** 
1. Check Profiling Output (`pre=?`)
2. Wenn `pre > 80%` → Normal für komplexe Indikatoren
3. Wenn `train_pf > 30%` → Bug! Melden!

---

## **✅ SUCCESS CRITERIA:**

**Phase 1 ist ERFOLGREICH wenn:**
1. ✅ Alle 595 Indikatoren getestet (oder SKIP/TIMEOUT dokumentiert)
2. ✅ CSV Files für alle erfolgreichen Indikatoren vorhanden
3. ✅ Profiling zeigt `pre > 70%` (Signal-Gen ist Bottleneck)
4. ✅ Daily DD ist korrekt (Prop-Firm-konform)
5. ✅ Keine Memory Leaks (RAM stabil)
6. ✅ Checkpoint System funktioniert (Resume nach Crash)

---

## **📊 NACH PHASE 1:**

### **1. VALIDIERUNG:**
```powershell
# Run validation script
python 08_Lazora_Verfahren\04_TOP1000_GENERATOR.py
```

### **2. HEATMAPS:**
```powershell
# Generate heatmaps
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 1h
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 30m
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 15m
python 08_Lazora_Verfahren\03_HEATMAP_VISUALIZER.py 5m
```

### **3. ANALYSE:**
- Top 1000 Rankings pro Symbol
- Top 1000 Overall (alle Symbole)
- Heatmaps für beste Indikatoren

---

## **🎯 NÄCHSTE SCHRITTE (NACH PHASE 1):**

**NICHT JETZT:**
- ❌ Dynamic Exit
- ❌ ATR-Based Exit
- ❌ 40 Symbole
- ❌ ProcessPool
- ❌ Regime Filter

**ERST DANN:**
1. ✅ Phase 1 Ergebnisse analysieren
2. ✅ Top 100 Indikatoren identifizieren
3. ✅ Phase 2 (Adaptive Refinement) planen
4. ✅ Phase 3 (Ultra-Fine Tuning) planen

---

**READY TO START! 🚀**

```powershell
python 08_Lazora_Verfahren\LAZORA_PHASE1_1H.py
```
