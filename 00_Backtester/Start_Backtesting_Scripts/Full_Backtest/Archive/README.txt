================================================================================
BACKTEST SCRIPTS - ORIGINAL SOURCES & DESCRIPTIONS
================================================================================

Erstellt: 2026-01-19
Zweck: Dokumentation der Original-Skripte aus Superindikator_Gamma

================================================================================
1. ORIGINAL_ELITE_BACKTEST_595x200x3x6.py
================================================================================
Quelle: /opt/Zenatus_Backtester\ELITE_BACKTEST_595x200x3x6.py

Beschreibung:
- Testet 595 Indikatoren x 200 Kombinationen x 3 Exit-Typen x 6 Symbole
- Verwendet Multiprocessing für maximale Geschwindigkeit
- Exit-Typen: Cross, Level, Multi
- ACHTUNG: Verwendet SIMULIERTE Preisdaten (Random Walk), keine echten!
- Speichert Ergebnisse in CSV und MD Format

================================================================================
2. ORIGINAL_ELITE_DEEP_DIVE_BACKTEST.py
================================================================================
Quelle: /opt/Zenatus_Backtester\ELITE_DEEP_DIVE_BACKTEST.py

Beschreibung:
- Elite Deep Dive für 332 Top-Indikatoren
- Bis zu 10.000 Kombinationen pro Indikator
- 4 Exit-Typen: Cross, Level, Multi, ATR-Volatility
- ATR-Multiplikatoren: [1.0, 1.5, 2.0, 2.5, 3.0]
- FTMO Spreads implementiert
- ACHTUNG: Verwendet SIMULIERTE Preisdaten (Random Walk), keine echten!

================================================================================
3. ORIGINAL_GENERATE_ELITE_COMBINATIONS.py
================================================================================
Quelle: /opt/Zenatus_Backtester\GENERATE_ELITE_COMBINATIONS.py

Beschreibung:
- Identifiziert Elite-Indikatoren aus Top-100-Berichten
- Generiert bis zu 10.000 feinkörnige Parameter-Kombinationen pro Indikator
- Verwendet intelligentes Grid-Sampling für gleichmäßige Verteilung
- Speichert Ergebnisse in ELITE_ALL_COMBINATIONS.json

================================================================================
4. ORIGINAL_master_600_parameter_optimizer.py
================================================================================
Quelle: /opt/Zenatus_Backtester\master_600_parameter_optimizer.py

Beschreibung:
- BESTER Parameter-Verteiler (5/5 Sterne)
- Mathematisch fundierte Strategien basierend auf Parameter-Typ:
  * period/length/window -> Fibonacci-Expansion
  * multiplier/std/factor -> Exponentielle Schritte
  * threshold/level/overbought -> Lineare Interpolation (15 Werte)
  * smooth/alpha/beta -> Primzahlen / Dezimal-Progression
  * tp_pips/sl_pips -> Trading-Pips [10,15,20,25,30,35,40,50,60,75,100,125,150,200]

================================================================================
NEUE SKRIPTE (ANGEPASST FÜR ALPHA):
================================================================================

FIXED_EXIT_SCANNER.py - Fixed TP/SL Exit (Entry=Indikator, Exit=TP/SL)
DYNAMIC_EXIT_SCANNER.py - Dynamic Exit (Entry=Indikator, Exit=Indikator-Signal)
MASTER_PIPELINE.py - Orchestriert alle 8 Kapitel automatisch

================================================================================
KONFIGURATION:
================================================================================

- Daten: Echte historische Daten aus 01_Data/Market_Data
- Zeitraum: 01.01.2023 bis Ende der verfügbaren Daten
- Symbole: AUD_USD, EUR_USD, GBP_USD, NZD_USD, USD_CAD, USD_CHF
- Startkapital: $10,000
- Investment pro Trade: $100
- Leverage: 1:10
- TP Range: 20-350 Pips
- SL Range: 10-175 Pips (50% von TP)

================================================================================
