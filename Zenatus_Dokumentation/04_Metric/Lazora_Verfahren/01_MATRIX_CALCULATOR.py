# -*- coding: utf-8 -*-
"""
LAZORA PHASE A - MATRIX CALCULATOR
===================================
Berechnet für jeden Indikator:
- Matrix Min/Max Ranges
- Totale Kombinationen (Entry × Exit)
- Update Parameter Handbook
"""

import sys
from pathlib import Path
import json
import pandas as pd

BASE_PATH = Path(r"D:\2_Trading\Superindikator_Alpha")
PARAM_PATH = BASE_PATH / "01_Backtest_System" / "Parameter_Optimization"
OUTPUT_PATH = BASE_PATH / "08_Lazora_Verfahren"

print("="*80)
print("LAZORA PHASE A - MATRIX CALCULATOR")
print("="*80)

# Load existing handbook
handbook_file = PARAM_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
with open(handbook_file, 'r', encoding='utf-8') as f:
    handbook = json.load(f)

print(f"\nLoaded {len(handbook)} indicators from handbook")

# Calculate Matrix Ranges for each indicator
matrix_data = []

for ind in handbook:
    ind_num = ind['Indicator_Num']
    ind_name = ind['Indicator_Name']
    entry_params = ind['Entry_Params']
    exit_params = ind['Exit_Params']
    
    # Entry Matrix
    entry_matrix = {}
    for param_name, param_config in entry_params.items():
        values = param_config['values']
        entry_matrix[param_name] = {
            'min': min(values),
            'max': max(values),
            'steps': len(values),
            'type': param_config['type'],
            'default': param_config.get('default', values[len(values)//2])
        }
    
    # Exit Matrix (TP/SL)
    exit_matrix = {}
    for param_name, param_config in exit_params.items():
        values = param_config['values']
        exit_matrix[param_name] = {
            'min': min(values),
            'max': max(values),
            'steps': len(values)
        }
    
    # Total Combinations
    entry_combos = ind['Total_Entry_Combinations']
    exit_combos = ind['Total_Exit_Combinations']
    total_combos = ind['Total_Combinations']
    
    # Matrix Info
    matrix_info = {
        'Indicator_Num': ind_num,
        'Indicator_Name': ind_name,
        'Entry_Matrix': entry_matrix,
        'Exit_Matrix': exit_matrix,
        'Entry_Combinations': entry_combos,
        'Exit_Combinations': exit_combos,
        'Total_Combinations': total_combos,
        'Dimensionality': len(entry_params),
        'Lazora_Phase1_Samples': 500,  # Sobol samples for Phase 1
        'Efficiency_Ratio': 500 / total_combos if total_combos > 0 else 0
    }
    
    matrix_data.append(matrix_info)
    
    print(f"\r[{ind_num:03d}/{len(handbook)}] {ind_name[:40]:40s} | {len(entry_params)}D | {total_combos:,} combos", end='', flush=True)

print("\n\nMatrix calculation complete!")

# Save Matrix Info
matrix_file = OUTPUT_PATH / "MATRIX_RANGES_COMPLETE.json"
with open(matrix_file, 'w', encoding='utf-8') as f:
    json.dump(matrix_data, f, indent=2)

print(f"Saved: {matrix_file}")

# Generate Summary CSV
summary_data = []
for m in matrix_data:
    row = {
        'Indicator_Num': m['Indicator_Num'],
        'Indicator_Name': m['Indicator_Name'],
        'Dimensionality': m['Dimensionality'],
        'Entry_Combinations': m['Entry_Combinations'],
        'Exit_Combinations': m['Exit_Combinations'],
        'Total_Combinations': m['Total_Combinations'],
        'Phase1_Samples': m['Lazora_Phase1_Samples'],
        'Efficiency_%': f"{m['Efficiency_Ratio']*100:.4f}%"
    }
    
    # Add Entry Matrix Info
    for i, (param_name, param_info) in enumerate(m['Entry_Matrix'].items(), 1):
        row[f'Param{i}_Name'] = param_name
        row[f'Param{i}_Min'] = param_info['min']
        row[f'Param{i}_Max'] = param_info['max']
        row[f'Param{i}_Default'] = param_info['default']
        row[f'Param{i}_Type'] = param_info['type']
    
    summary_data.append(row)

df_summary = pd.DataFrame(summary_data)
summary_file = OUTPUT_PATH / "MATRIX_SUMMARY.csv"
df_summary.to_csv(summary_file, index=False)

print(f"Summary: {summary_file}")

# Statistics
print(f"\n{'='*80}")
print("STATISTICS:")
print(f"{'='*80}")
print(f"Total Indicators: {len(matrix_data)}")
print(f"Avg Dimensionality: {sum([m['Dimensionality'] for m in matrix_data])/len(matrix_data):.1f}D")
print(f"Avg Total Combos: {sum([m['Total_Combinations'] for m in matrix_data])/len(matrix_data):,.0f}")
print(f"Max Combos: {max([m['Total_Combinations'] for m in matrix_data]):,} ({max(matrix_data, key=lambda x: x['Total_Combinations'])['Indicator_Name']})")
print(f"Min Combos: {min([m['Total_Combinations'] for m in matrix_data]):,} ({min(matrix_data, key=lambda x: x['Total_Combinations'])['Indicator_Name']})")
print(f"Avg Efficiency (500 samples): {sum([m['Efficiency_Ratio'] for m in matrix_data])/len(matrix_data)*100:.4f}%")
print(f"{'='*80}")

print("\n✅ DONE! Matrix ranges calculated for all indicators.")
print(f"Next: Generate Wörterbuch entries")
