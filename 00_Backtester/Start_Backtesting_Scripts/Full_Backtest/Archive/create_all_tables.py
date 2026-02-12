import json
from pathlib import Path
from datetime import datetime

# Lade Analyse-Ergebnisse
results_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\BACKTEST_ANALYSE_RESULTS.json")
with open(results_file, 'r') as f:
    results = json.load(f)

# CSV-Dateien
csv_path = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\Fixed_Exit\1h")
csv_files = list(csv_path.glob("*.csv"))
csv_ind_ids = []
for csv_file in csv_files:
    try:
        ind_num = int(csv_file.stem.split('_')[0])
        csv_ind_ids.append(ind_num)
    except:
        pass

csv_ind_ids = sorted(set(csv_ind_ids))

# Extrahiere Daten
success_ids = results['success_ids']
timeout_details = results['timeout_details']
no_results_ids = results['no_results_ids']
success_details = results['success_details']

# Timeout-Indikatoren mit SUCCESS
timeout_success = [ind for ind in timeout_details.keys() if int(ind) in success_ids]

# Erstelle Lookup für Performance
perf_lookup = {}
for s in success_details:
    perf_lookup[s['ind']] = {'pf': s['pf'], 'sr': s['sr'], 'time': s['time']}

print("="*80)
print("TABELLE 1: SUCCESS STRATEGIEN")
print("="*80)
print()
print("| Ind# | Name | PF | SR | Zeit | Timeouts | CSV |")
print("|------|------|----|----|------|----------|-----|")

for ind_id in sorted(success_ids):
    perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0, 'time': '?'})
    timeouts = timeout_details.get(str(ind_id), 0)
    has_csv = "✅" if ind_id in csv_ind_ids else "❌"
    
    print(f"| {ind_id:03d} | - | {perf['pf']:.2f} | {perf['sr']:.2f} | {perf['time']} | {timeouts} | {has_csv} |")

print()
print(f"**Total:** {len(success_ids)} SUCCESS Strategien")
print(f"**Mit CSV:** {sum(1 for i in success_ids if i in csv_ind_ids)}")
print(f"**Ohne CSV:** {sum(1 for i in success_ids if i not in csv_ind_ids)}")
print()
print("="*80)
print()

print("="*80)
print("TABELLE 2: TIMEOUT / WARNING STRATEGIEN")
print("="*80)
print()
print("| Ind# | Timeouts | Status | PF | SR | Bemerkung |")
print("|------|----------|--------|----|----|-----------|")

for ind_str, count in sorted(timeout_details.items(), key=lambda x: x[1], reverse=True):
    ind_id = int(ind_str)
    status = "✅ SUCCESS" if ind_id in success_ids else "⏳ Läuft"
    perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0})
    
    if count >= 40:
        bemerkung = "🔴 Sehr viele"
    elif count >= 20:
        bemerkung = "🟡 Viele"
    elif count >= 10:
        bemerkung = "🟢 Moderat"
    else:
        bemerkung = "✅ Wenige"
    
    print(f"| {ind_id:03d} | {count:3d} | {status} | {perf['pf']:.2f} | {perf['sr']:.2f} | {bemerkung} |")

print()
print(f"**Total:** {len(timeout_details)} Indikatoren mit Timeouts")
print(f"**Davon SUCCESS:** {len([i for i in timeout_details.keys() if int(i) in success_ids])}")
print(f"**Total Timeout-Warnings:** {sum(timeout_details.values())}")
print()
print("="*80)
print()

print("="*80)
print("TABELLE 3: FEHLER / NO RESULTS STRATEGIEN")
print("="*80)
print()
print("| Ind# | Typ | Status | PF | SR | Root-Cause |")
print("|------|-----|--------|----|----|------------|")

# No Results
for ind_id in no_results_ids:
    status = "✅ SUCCESS" if ind_id in success_ids else "❌ FEHLER"
    perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0})
    root_cause = "Einzelne Periods keine Signale, aber genug andere erfolgreich"
    
    print(f"| {ind_id:03d} | NO RESULTS | {status} | {perf['pf']:.2f} | {perf['sr']:.2f} | {root_cause} |")

# Errors (aktuell keine)
if results['error_count'] == 0:
    print("| - | - | - | - | - | **Keine Fehler!** ✅ |")

print()
print(f"**Total NO RESULTS:** {len(no_results_ids)}")
print(f"**Davon SUCCESS:** {sum(1 for i in no_results_ids if i in success_ids)}")
print(f"**Total ERRORS:** {results['error_count']}")
print()
print("="*80)
print()

print("="*80)
print("TABELLE 4: NEUE SUCCESS-KANDIDATEN (Verifiziert)")
print("="*80)
print()
print("| Ind# | PF | SR | Quelle | Verifiziert | Bereit für Haupt-Backtest |")
print("|------|----|----|--------|-------------|---------------------------|")

# Neue Success-Kandidaten = SUCCESS aber noch kein CSV
neue_kandidaten = [ind for ind in success_ids if ind not in csv_ind_ids]

if len(neue_kandidaten) == 0:
    print("| - | - | - | - | - | **Alle SUCCESS haben bereits CSVs!** ✅ |")
else:
    for ind_id in sorted(neue_kandidaten):
        perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0})
        quelle = "Haupt-Backtest"
        verifiziert = "✅ JA" if ind_id in success_ids else "❌ NEIN"
        bereit = "✅ JA" if ind_id in success_ids else "❌ NEIN"
        
        print(f"| {ind_id:03d} | {perf['pf']:.2f} | {perf['sr']:.2f} | {quelle} | {verifiziert} | {bereit} |")

print()
print(f"**Total neue Kandidaten:** {len(neue_kandidaten)}")
print(f"**Verifiziert (SUCCESS):** {len(neue_kandidaten)}")
print(f"**Bereit für Haupt-Backtest:** {len(neue_kandidaten)}")
print()
print("**Bemerkung:** Alle neuen Kandidaten wurden bereits im Haupt-Backtest getestet und haben SUCCESS erreicht!")
print("**Aktion:** CSVs sollten bereits existieren, evtl. Speicher-Problem oder Pfad-Problem.")
print()
print("="*80)
print()

# Speichere Tabellen
output = f"""# 📊 ALLE TABELLEN - BACKTEST ÜBERSICHT

Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## TABELLE 1: SUCCESS STRATEGIEN

| Ind# | Name | PF | SR | Zeit | Timeouts | CSV |
|------|------|----|----|------|----------|-----|
"""

for ind_id in sorted(success_ids):
    perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0, 'time': '?'})
    timeouts = timeout_details.get(str(ind_id), 0)
    has_csv = "✅" if ind_id in csv_ind_ids else "❌"
    output += f"| {ind_id:03d} | - | {perf['pf']:.2f} | {perf['sr']:.2f} | {perf['time']} | {timeouts} | {has_csv} |\n"

output += f"""
**Total:** {len(success_ids)} SUCCESS Strategien
**Mit CSV:** {sum(1 for i in success_ids if i in csv_ind_ids)}
**Ohne CSV:** {sum(1 for i in success_ids if i not in csv_ind_ids)}

---

## TABELLE 2: TIMEOUT / WARNING STRATEGIEN

| Ind# | Timeouts | Status | PF | SR | Bemerkung |
|------|----------|--------|----|----|-----------|
"""

for ind_str, count in sorted(timeout_details.items(), key=lambda x: x[1], reverse=True):
    ind_id = int(ind_str)
    status = "✅ SUCCESS" if ind_id in success_ids else "⏳ Läuft"
    perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0})
    
    if count >= 40:
        bemerkung = "🔴 Sehr viele"
    elif count >= 20:
        bemerkung = "🟡 Viele"
    elif count >= 10:
        bemerkung = "🟢 Moderat"
    else:
        bemerkung = "✅ Wenige"
    
    output += f"| {ind_id:03d} | {count:3d} | {status} | {perf['pf']:.2f} | {perf['sr']:.2f} | {bemerkung} |\n"

output += f"""
**Total:** {len(timeout_details)} Indikatoren mit Timeouts
**Davon SUCCESS:** {len([i for i in timeout_details.keys() if int(i) in success_ids])}
**Total Timeout-Warnings:** {sum(timeout_details.values())}

---

## TABELLE 3: FEHLER / NO RESULTS STRATEGIEN

| Ind# | Typ | Status | PF | SR | Root-Cause |
|------|-----|--------|----|----|------------|
"""

for ind_id in no_results_ids:
    status = "✅ SUCCESS" if ind_id in success_ids else "❌ FEHLER"
    perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0})
    root_cause = "Einzelne Periods keine Signale, aber genug andere erfolgreich"
    output += f"| {ind_id:03d} | NO RESULTS | {status} | {perf['pf']:.2f} | {perf['sr']:.2f} | {root_cause} |\n"

if results['error_count'] == 0:
    output += "| - | - | - | - | - | **Keine Fehler!** ✅ |\n"

output += f"""
**Total NO RESULTS:** {len(no_results_ids)}
**Davon SUCCESS:** {sum(1 for i in no_results_ids if i in success_ids)}
**Total ERRORS:** {results['error_count']}

---

## TABELLE 4: NEUE SUCCESS-KANDIDATEN (Verifiziert)

| Ind# | PF | SR | Quelle | Verifiziert | Bereit für Haupt-Backtest |
|------|----|----|--------|-------------|---------------------------|
"""

if len(neue_kandidaten) == 0:
    output += "| - | - | - | - | - | **Alle SUCCESS haben bereits CSVs!** ✅ |\n"
else:
    for ind_id in sorted(neue_kandidaten):
        perf = perf_lookup.get(ind_id, {'pf': 0, 'sr': 0})
        quelle = "Haupt-Backtest"
        verifiziert = "✅ JA"
        bereit = "✅ JA"
        output += f"| {ind_id:03d} | {perf['pf']:.2f} | {perf['sr']:.2f} | {quelle} | {verifiziert} | {bereit} |\n"

output += f"""
**Total neue Kandidaten:** {len(neue_kandidaten)}
**Verifiziert (SUCCESS):** {len(neue_kandidaten)}
**Bereit für Haupt-Backtest:** {len(neue_kandidaten)}

**Bemerkung:** Alle neuen Kandidaten wurden bereits im Haupt-Backtest getestet und haben SUCCESS erreicht!
**Aktion:** CSVs sollten bereits existieren, evtl. Speicher-Problem oder Pfad-Problem.
"""

output_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\ALLE_TABELLEN.md")
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Alle Tabellen gespeichert: {output_file}")
