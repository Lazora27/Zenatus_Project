import json
from pathlib import Path

# Pfade
problem_json = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\INDICATORS_PROBLEM_2COMBOS.json")
status_json = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\INDICATOR_STATUS_ANALYSIS.json")
results_json = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\BACKTEST_ANALYSE_RESULTS.json")

# Lade Daten
with open(problem_json, 'r') as f:
    problem_data = json.load(f)

with open(status_json, 'r') as f:
    status_data = json.load(f)

with open(results_json, 'r') as f:
    results_data = json.load(f)

# 20 Timeout-SUCCESS Indikatoren
timeout_success = status_data['timeout_success_ids']

# 59 fertige SUCCESS
finished_success = results_data['success_ids']

print("="*80)
print("PROBLEM-PIPELINE UPDATE")
print("="*80)
print()

# Aktuelle Problem-Indikatoren
current_problems = list(problem_data.keys())
current_problems_int = [int(k) for k in current_problems]

print(f"Aktuelle Problem-Indikatoren: {len(current_problems)}")
print()

# Entferne 59 fertige SUCCESS
to_remove = [ind for ind in finished_success if ind in current_problems_int]
print(f"Zu entfernen (fertige SUCCESS): {len(to_remove)}")
for ind in to_remove[:10]:
    print(f"  Ind#{ind:03d}")
if len(to_remove) > 10:
    print(f"  ... und {len(to_remove) - 10} weitere")
print()

# Füge 20 Timeout-SUCCESS hinzu (falls nicht schon drin)
to_add = [ind for ind in timeout_success if ind not in current_problems_int]
print(f"Hinzuzufügen (Timeout-SUCCESS): {len(to_add)}")
for ind in to_add:
    timeouts = results_data['timeout_details'].get(str(ind), 0)
    print(f"  Ind#{ind:03d}: {timeouts} Timeouts")
print()

# Erstelle neue Problem-Liste
new_problem_data = {}

# Behalte nur Indikatoren die nicht in finished_success sind
for ind_str, config in problem_data.items():
    ind_id = int(ind_str)
    if ind_id not in finished_success:
        new_problem_data[ind_str] = config

# Füge Timeout-SUCCESS hinzu
for ind in to_add:
    timeouts = results_data['timeout_details'].get(str(ind), 0)
    
    # Erstelle Config mit 30-Prompt JSON Struktur
    new_problem_data[str(ind)] = {
        "indicator_type": "timeout_success",
        "entry_parameters": {
            "period": {
                "values": [10, 20, 30],
                "optimal": [20]
            }
        },
        "exit_parameters": {
            "tp_pips": {
                "values": [50, 100],
                "optimal": [75]
            },
            "sl_pips": {
                "values": [30, 50],
                "optimal": [40]
            }
        },
        "note": f"Timeout-SUCCESS indicator with {timeouts} timeouts - optimized for re-test"
    }

print("="*80)
print("NEUE PROBLEM-LISTE:")
print("="*80)
print(f"Vorher: {len(current_problems)} Indikatoren")
print(f"Entfernt: {len(to_remove)} (fertige SUCCESS)")
print(f"Hinzugefügt: {len(to_add)} (Timeout-SUCCESS)")
print(f"Nachher: {len(new_problem_data)} Indikatoren")
print()

# Speichere neue Problem-Liste
backup_file = problem_json.parent / f"{problem_json.stem}_BACKUP.json"
with open(backup_file, 'w') as f:
    json.dump(problem_data, f, indent=2)
print(f"Backup erstellt: {backup_file}")

with open(problem_json, 'w') as f:
    json.dump(new_problem_data, f, indent=2)
print(f"Neue Problem-Liste gespeichert: {problem_json}")
print()

# Zusammenfassung
print("="*80)
print("ZUSAMMENFASSUNG:")
print("="*80)
print(f"✅ {len(to_remove)} fertige SUCCESS aus Pipeline entfernt")
print(f"✅ {len(to_add)} Timeout-SUCCESS zur Pipeline hinzugefügt")
print(f"✅ Neue Pipeline: {len(new_problem_data)} Indikatoren")
print()
print("Nächster Schritt:")
print("  Haupt-Backtest neu starten mit optimierten Configs")
print("  für die 20 Timeout-SUCCESS Indikatoren")
