# -*- coding: utf-8 -*-
"""
GENERATE ELITE COMBINATIONS

1. Identifiziert die 332 Elite-Indikatoren aus den Top-100-Berichten.
2. Generiert für jeden dieser Indikatoren bis zu 10.000 feinkörnige, 
   gleichmäßig verteilte Parameter-Kombinationen.
3. Speichert das Ergebnis in 'ELITE_ALL_COMBINATIONS.json'.
"""

import pandas as pd
import numpy as np
import json
from itertools import product
import math

print("="*80)
print("GENERATE ELITE COMBINATIONS (332 Indikatoren, bis zu 10.000 Kombis)")
print("="*80)

def get_elite_indicator_ids():
    """Lädt die 7 Berichte und extrahiert die einzigartigen Indikator-IDs aus den Top 100."""
    print("\nSchritt 1: Identifiziere die 332 Elite-Indikatoren...")
    files = [
        'REPORT_TOP_1000_OVERALL.csv', 'REPORT_TOP_1000_USD_CAD.csv',
        'REPORT_TOP_1000_EUR_USD.csv', 'REPORT_TOP_1000_GBP_USD.csv',
        'REPORT_TOP_1000_AUD_USD.csv', 'REPORT_TOP_1000_NZD_USD.csv',
        'REPORT_TOP_1000_USD_CHF.csv'
    ]
    all_dfs_top100 = []
    for file in files:
        try:
            df = pd.read_csv(file)
            all_dfs_top100.append(df.head(100))
        except FileNotFoundError:
            print(f"  - WARNUNG: Datei nicht gefunden: {file}")
            return None

    combined_df = pd.concat(all_dfs_top100, ignore_index=True)
    elite_ids = sorted(combined_df['indicator_id'].unique())
    print(f"  - {len(elite_ids)} einzigartige Elite-Indikatoren gefunden.")
    return [f"{i:03d}" for i in elite_ids]

def generate_flexible_combinations(ind_data, max_combinations=10000):
    """Generiert eine flexible Anzahl von Kombinationen, maximal jedoch max_combinations."""
    param_ranges = ind_data['ranges']
    param_names = list(param_ranges.keys())
    num_params = len(param_names)

    if num_params == 0:
        return [{'default': 'default'}] # Fallback

    # Berechne die Gesamtzahl der möglichen Kombinationen im vollen Grid
    total_possible_combos = 1
    for p_name in param_names:
        total_possible_combos *= len(param_ranges[p_name]['values'])

    # Bestimme die Zielanzahl der Kombinationen
    target_combinations = min(total_possible_combos, max_combinations)

    if target_combinations == 0:
        return []

    # Berechne die optimale Grid-Größe pro Parameter für die Ziel-Kombinationen
    grid_size_per_param = int(np.ceil(target_combinations ** (1.0 / num_params)))

    param_grids = {}
    for param_name in param_names:
        values = param_ranges[param_name]['values']
        if len(values) >= grid_size_per_param:
            indices = np.linspace(0, len(values) - 1, grid_size_per_param).astype(int)
            grid = [values[i] for i in indices]
        else:
            grid = values
        param_grids[param_name] = grid

    # Erstelle alle Grid-Kombinationen
    grid_values = [param_grids[p] for p in param_names]
    all_combos_from_grid = list(product(*grid_values))

    # Sample exakt target_combinations gleichmäßig aus dem erstellten Grid
    if len(all_combos_from_grid) > target_combinations:
        indices = np.linspace(0, len(all_combos_from_grid) - 1, target_combinations).astype(int)
        sampled_combos = [all_combos_from_grid[i] for i in indices]
    else:
        sampled_combos = all_combos_from_grid

    combinations = [
        {param_names[i]: combo[i] for i in range(num_params)}
        for combo in sampled_combos
    ]

    return combinations

# --- MAIN EXECUTION --- #

# 1. Elite-Indikatoren holen
elite_indicator_ids = get_elite_indicator_ids()

if elite_indicator_ids:
    # 2. Parameter-Ranges laden
    print("\nSchritt 2: Lade Parameter-Ranges...")
    try:
        with open('INTELLIGENT_PARAMETER_RANGES.json', 'r', encoding='utf-8') as f:
            all_ranges = json.load(f)['ranges']
        print("  - Parameter-Ranges geladen.")

        # 3. Kombinationen generieren
        print("\nSchritt 3: Generiere bis zu 10.000 Kombinationen pro Elite-Indikator...")
        elite_combinations = {}
        total_generated_combos = 0

        for i, ind_id in enumerate(elite_indicator_ids, 1):
            if ind_id in all_ranges:
                ind_data = all_ranges[ind_id]
                combinations = generate_flexible_combinations(ind_data, max_combinations=10000)
                
                elite_combinations[ind_id] = {
                    'name': ind_data['name'],
                    'class': ind_data['class'],
                    'param_count': len(ind_data['ranges']),
                    'combinations': combinations,
                    'combination_count': len(combinations)
                }
                total_generated_combos += len(combinations)
                if i % 50 == 0:
                    print(f"  [{i:3d}/{len(elite_indicator_ids)}] Indikator {ind_id}: {len(combinations):,d} Kombinationen generiert.")
            else:
                print(f"  - WARNUNG: Keine Ranges für Indikator {ind_id} gefunden.")

        # 4. Ergebnisse speichern
        print("\nSchritt 4: Speichere Ergebnisse...")
        output_file = 'ELITE_ALL_COMBINATIONS.json'
        output_data = {
            'statistics': {
                'total_indicators': len(elite_combinations),
                'total_combinations': total_generated_combos
            },
            'combinations': elite_combinations
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n{'='*80}")
        print("ERFOLGREICH ABGESCHLOSSEN")
        print(f"{'='*80}")
        print(f"  Elite-Indikatoren verarbeitet: {len(elite_combinations)}")
        print(f"  Gesamte Kombinationen generiert: {total_generated_combos:,d}")
        print(f"  Daten gespeichert in: {output_file}")
        print(f"\nNÄCHSTER SCHRITT: Implementierung der neuen Exit-Typen.")
        print(f"{'='*80}")

    except FileNotFoundError:
        print("\nFEHLER: 'INTELLIGENT_PARAMETER_RANGES.json' nicht gefunden. Abbruch.")
