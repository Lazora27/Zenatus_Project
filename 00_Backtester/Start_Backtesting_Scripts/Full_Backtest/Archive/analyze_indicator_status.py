import json
from pathlib import Path

# Pfade
unique_path = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
skip_list_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\SKIP_LIST_CORRECT.json")
results_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\BACKTEST_ANALYSE_RESULTS.json")

# Lade SKIP_LIST
with open(skip_list_file, 'r') as f:
    skip_data = json.load(f)

# Lade Backtest-Ergebnisse
with open(results_file, 'r') as f:
    results = json.load(f)

# Alle Unique Indikatoren
all_indicators = []
for py_file in unique_path.glob("*.py"):
    if py_file.stem != "__pycache__":
        try:
            ind_num = int(py_file.stem.split('_')[0])
            all_indicators.append(ind_num)
        except:
            pass

all_indicators = sorted(set(all_indicators))

# Extrahiere Listen
skip_indicators = set(skip_data['skip_indicators'])
stable_success = set(skip_data['stable_success'])
already_tested = set(skip_data['already_tested'])
problem_indicators = set(skip_data['problem_indicators'])

# Neue SUCCESS aus aktuellem Backtest
new_success = set(results['success_ids'])

# Timeout-Indikatoren mit SUCCESS
timeout_success = []
for ind_str, count in results['timeout_details'].items():
    ind_id = int(ind_str)
    if ind_id in new_success:
        timeout_success.append(ind_id)

timeout_success = sorted(timeout_success)

print("="*80)
print("INDIKATOR-STATUS ANALYSE")
print("="*80)
print()

print("UNIQUE INDIKATOREN:")
print(f"Total .py Dateien: {len(all_indicators)}")
print(f"IDs Range: {min(all_indicators)} - {max(all_indicators)}")
print()

print("SKIP_LIST KATEGORIEN:")
print(f"skip_indicators: {len(skip_indicators)}")
print(f"stable_success: {len(stable_success)}")
print(f"already_tested: {len(already_tested)}")
print(f"problem_indicators: {len(problem_indicators)}")
print()

print("AKTUELLER BACKTEST:")
print(f"Neue SUCCESS: {len(new_success)}")
print(f"Davon Timeout-SUCCESS: {len(timeout_success)}")
print()

# Berechne Differenzen
total_tested = stable_success | already_tested | new_success
not_tested = set(all_indicators) - total_tested - skip_indicators

print("ZUSAMMENFASSUNG:")
print(f"Total Unique Indikatoren: {len(all_indicators)}")
print(f"Skip (nicht testen): {len(skip_indicators)}")
print(f"Stable SUCCESS (alt): {len(stable_success)}")
print(f"Already Tested (alt): {len(already_tested)}")
print(f"Neue SUCCESS (aktuell): {len(new_success)}")
print(f"Total getestet: {len(total_tested)}")
print(f"Noch nicht getestet: {len(not_tested)}")
print()

# Vergleichstabelle
print("="*80)
print("VERGLEICHSTABELLE: 595 → 473 → 235")
print("="*80)
print()

# 595 = Alle Indikatoren (inkl. Duplikate)
total_595 = 595

# 473 = Unique (non-duplicates)
total_473 = len(all_indicators)

# 235 = Bereits getestet (stable + already + new)
total_235 = len(total_tested)

# Differenz
diff_595_473 = total_595 - total_473
diff_473_235 = total_473 - total_235

print(f"595 Original Indikatoren")
print(f"  ↓ -{diff_595_473} (Mathematische Duplikate)")
print(f"473 Unique Indikatoren (Backup_04/Unique)")
print(f"  ↓ -{len(skip_indicators)} (Skip - nicht testen)")
print(f"{total_473 - len(skip_indicators)} Testbare Indikatoren")
print(f"  ↓ -{total_235} (Bereits getestet)")
print(f"{diff_473_235} Noch zu testen")
print()

print("DETAILLIERTE AUFSCHLÜSSELUNG:")
print(f"473 Unique Indikatoren")
print(f"  - {len(skip_indicators)} Skip (nicht testen)")
print(f"  = {total_473 - len(skip_indicators)} Testbar")
print()
print(f"{total_473 - len(skip_indicators)} Testbar")
print(f"  - {len(stable_success)} Stable SUCCESS (alt)")
print(f"  - {len(already_tested)} Already Tested (alt)")
print(f"  - {len(new_success)} Neue SUCCESS (aktuell)")
print(f"  = {diff_473_235} Noch zu testen")
print()

# Finde die 238 nicht getesteten
not_tested_sorted = sorted(not_tested)

print("="*80)
print(f"DIE {len(not_tested)} NOCH NICHT GETESTETEN INDIKATOREN:")
print("="*80)
print()

# Gruppiere in Ranges
ranges = []
start = None
prev = None
for ind in not_tested_sorted:
    if start is None:
        start = ind
        prev = ind
    elif ind == prev + 1:
        prev = ind
    else:
        if start == prev:
            ranges.append(f"{start}")
        else:
            ranges.append(f"{start}-{prev}")
        start = ind
        prev = ind

if start is not None:
    if start == prev:
        ranges.append(f"{start}")
    else:
        ranges.append(f"{start}-{prev}")

print("Ranges:")
for r in ranges:
    print(f"  {r}")
print()

# Erste 20 und letzte 20
print("Erste 20:")
for ind in not_tested_sorted[:20]:
    print(f"  Ind#{ind:03d}")
print()

if len(not_tested_sorted) > 40:
    print("...")
    print()
    print("Letzte 20:")
    for ind in not_tested_sorted[-20:]:
        print(f"  Ind#{ind:03d}")
    print()

# Timeout-SUCCESS Indikatoren
print("="*80)
print(f"23 TIMEOUT-SUCCESS INDIKATOREN (für Pipeline):")
print("="*80)
print()
for ind in timeout_success:
    timeouts = results['timeout_details'].get(str(ind), 0)
    print(f"  Ind#{ind:03d}: {timeouts} Timeouts")
print()

# Speichere Ergebnisse
output = {
    'total_unique': len(all_indicators),
    'skip_count': len(skip_indicators),
    'stable_success_count': len(stable_success),
    'already_tested_count': len(already_tested),
    'new_success_count': len(new_success),
    'total_tested': len(total_tested),
    'not_tested_count': len(not_tested),
    'not_tested_ids': not_tested_sorted,
    'timeout_success_ids': timeout_success,
    'comparison': {
        '595_original': total_595,
        '473_unique': total_473,
        '235_tested': total_235,
        'diff_595_473': diff_595_473,
        'diff_473_235': diff_473_235
    }
}

output_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\INDICATOR_STATUS_ANALYSIS.json")
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Ergebnisse gespeichert: {output_file}")
