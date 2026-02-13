# Zenatus Backtester - Windows Start Guide

## Voraussetzungen (Prerequisites)
1. **Python 3.10+** muss installiert sein. [Download hier](https://www.python.org/downloads/)
   - **WICHTIG:** Beim Installieren "Add Python to PATH" anhaken!

## Starten

Es gibt zwei Wege das Programm zu starten. Versuche zuerst Weg A.

### Weg A: Doppelklick (Batch)
1. Öffne den Ordner `Zenatus_Backtester`.
2. Doppelklick auf **`WINDOWS_RUN.bat`**.
3. Ein schwarzes Fenster öffnet sich, installiert Updates und startet den Browser.

### Weg B: Rechtsklick (PowerShell) - Falls Weg A nicht geht
1. Öffne den Ordner `Zenatus_Backtester`.
2. Rechtsklick auf **`WINDOWS_RUN.ps1`**.
3. Wähle **"Mit PowerShell ausführen"** (Run with PowerShell).

## Fehlerbehebung

- **"Python not found"**: Installiere Python neu und hake "Add to PATH" an.
- **Fenster schließt sich sofort**: Mache einen Rechtsklick auf die Datei -> Bearbeiten -> füge `PAUSE` am Ende hinzu, um den Fehler zu lesen.
- **Browser öffnet nicht**: Kopiere die URL (z.B. `http://localhost:8501`), die im schwarzen Fenster angezeigt wird, in deinen Browser.

## Config
Die Einstellungen für den lokalen Modus befinden sich in `config/config.windows.yaml`.
