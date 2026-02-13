# GUI Feature Requests & Roadmap

Dies ist eine Checkliste für die weitere Entwicklung der Benutzeroberfläche. Bitte ankreuzen [x], was als nächstes erledigt werden soll.

## 1. Strategie-Auswahl
- [x] Laden von .json Dateien aus `Zenatus_Dokumentation/Listing`
- [ ] Parsen von Log-Dateien (failed/success) als Auswahlquelle
- [ ] Drag & Drop Upload neuer Strategien
- [ ] Editor zum direkten Bearbeiten der JSON-Parameter in der GUI

## 2. Backtest Parameter
- [x] Timeframe Slider (1m - 1d)
- [x] Datumsauswahl (Start - Ende)
- [x] Startkapital Eingabe
- [x] Spreads & Fees Auswahl (aus CSV)
- [X ] Multi-Select für Timeframes (Batch-Test)

## 3. Steuerung & Prozess
- [x] Start / Pause / Stop Buttons
- [ ] Echtzeit-Verbindung zum `pipeline_orchestrator.py` (derzeit Simulation)
- [ ] Anzeige der Docker-Logs in der GUI (Live-Console)

## 4. Analyse & Ergebnisse
- [ ] Interaktiver Chart (Candlesticks + Trades)
- [ ] Performance-Metriken Tabelle (Sharpe, Drawdown, Winrate)
- [ ] Export der Ergebnisse als PDF/HTML Report
- [ ] Vergleich von zwei Backtest-Läufen

## 5. Design & UX
- [x] Dark Mode (Standard)
- [x] Responsive Layout (Columns)
- [ ] Custom Branding (Logo, Farben)
- [ ] Mobile-Optimierung
