import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(r"/opt/Zenatus_Dokumentation\LOG\problem_fix_1h_20260131_035953.log")

# Lese komplettes Log
with open(LOG_FILE, 'r', encoding='utf-8') as f:
    logs = f.read()

# Extrahiere alle Einträge mit Timestamps
lines = logs.split('\n')

# Kategorien
success_inds = []
timeout_inds = defaultdict(int)
error_inds = []
no_results_inds = []

# Zeitfenster
time_04_00 = datetime.strptime("04:00:00", "%H:%M:%S").time()
time_heute_04_00 = datetime.strptime("04:00:00", "%H:%M:%S").time()
time_jetzt = datetime.now().time()

success_seit_04_00 = []
success_24h = []
success_heute = []

for line in lines:
    # Extrahiere Timestamp
    timestamp_match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]', line)
    if not timestamp_match:
        continue
    
    timestamp_str = timestamp_match.group(1)
    timestamp = datetime.strptime(timestamp_str, "%H:%M:%S").time()
    
    # SUCCESS
    if '[SUCCESS]' in line:
        match = re.search(r'Ind#(\d+).*ERFOLG.*combos.*PF=([\d.]+).*SR=([\d.]+)', line)
        if match:
            ind_num = int(match.group(1))
            pf = float(match.group(2))
            sr = float(match.group(3))
            
            success_inds.append({
                'ind': ind_num,
                'time': timestamp_str,
                'pf': pf,
                'sr': sr
            })
            
            # Zeitfenster-Kategorisierung
            if timestamp >= time_04_00:
                success_seit_04_00.append(ind_num)
                
                # Heute (nach 04:00)
                if timestamp >= time_heute_04_00:
                    success_heute.append(ind_num)
    
    # TIMEOUT
    elif 'VectorBT TIMEOUT' in line:
        match = re.search(r'Ind#(\d+)', line)
        if match:
            ind_num = int(match.group(1))
            timeout_inds[ind_num] += 1
    
    # ERROR
    elif '[ERROR]' in line and 'Ind#' in line:
        match = re.search(r'Ind#(\d+)', line)
        if match:
            ind_num = int(match.group(1))
            if ind_num not in error_inds:
                error_inds.append(ind_num)
    
    # NO RESULTS
    elif 'Keine Ergebnisse' in line or 'KEINE ERGEBNISSE' in line:
        match = re.search(r'Ind#(\d+)', line)
        if match:
            ind_num = int(match.group(1))
            if ind_num not in no_results_inds:
                no_results_inds.append(ind_num)

# Berechne 24h Fenster (alle SUCCESS)
success_24h = [s['ind'] for s in success_inds]

print("="*80)
print("HAUPT-BACKTEST ANALYSE")
print("="*80)
print(f"Log-Datei: {LOG_FILE.name}")
print(f"Analyse-Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

print("SUCCESS STATISTIKEN:")
print("-"*80)
print(f"Total SUCCESS: {len(success_inds)}")
print(f"SUCCESS seit 04:00 Uhr (Start): {len(success_seit_04_00)}")
print(f"SUCCESS letzte 24h: {len(success_24h)}")
print(f"SUCCESS heute (seit 04:00): {len(success_heute)}")
print()

print("TIMEOUT STATISTIKEN:")
print("-"*80)
print(f"Unique Indikatoren mit Timeouts: {len(timeout_inds)}")
print(f"Total Timeout-Warnings: {sum(timeout_inds.values())}")
print()
print("Top 10 Timeout-Indikatoren:")
for ind, count in sorted(timeout_inds.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  Ind#{ind:03d}: {count:3d} Timeouts")
print()

print("ERROR STATISTIKEN:")
print("-"*80)
print(f"Indikatoren mit ERRORS: {len(error_inds)}")
if error_inds:
    print(f"ERROR IDs: {sorted(error_inds)}")
print()

print("NO RESULTS STATISTIKEN:")
print("-"*80)
print(f"Indikatoren mit 'Keine Ergebnisse': {len(no_results_inds)}")
if no_results_inds:
    print(f"NO RESULTS IDs: {sorted(no_results_inds)}")
print()

print("LETZTE 10 SUCCESS:")
print("-"*80)
for s in success_inds[-10:]:
    print(f"[{s['time']}] Ind#{s['ind']:03d}: PF={s['pf']:.2f}, SR={s['sr']:.2f}")
print()

# Speichere Ergebnisse
import json

results = {
    'total_success': len(success_inds),
    'success_seit_04_00': len(success_seit_04_00),
    'success_24h': len(success_24h),
    'success_heute': len(success_heute),
    'success_ids': [s['ind'] for s in success_inds],
    'success_seit_04_00_ids': success_seit_04_00,
    'success_heute_ids': success_heute,
    'timeout_count': len(timeout_inds),
    'timeout_total_warnings': sum(timeout_inds.values()),
    'timeout_details': dict(timeout_inds),
    'error_count': len(error_inds),
    'error_ids': sorted(error_inds),
    'no_results_count': len(no_results_inds),
    'no_results_ids': sorted(no_results_inds),
    'success_details': success_inds
}

output_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\BACKTEST_ANALYSE_RESULTS.json")
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"Ergebnisse gespeichert: {output_file}")
