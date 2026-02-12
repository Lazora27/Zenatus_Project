# -*- coding: utf-8 -*-
"""
WÖRTERBUCH GENERATOR - INDICATOR ENCYCLOPEDIA
==============================================
Erstellt strukturierte Dokumentation für alle 595 Indikatoren
Mit Standard-Werten, Matrix-Ranges, und Kombinationen
"""

import sys
from pathlib import Path
import json
import pandas as pd

BASE_PATH = Path(r"D:\2_Trading\Superindikator_Alpha")
LAZORA_PATH = BASE_PATH / "08_Lazora_Verfahren"
OUTPUT_PATH = BASE_PATH / "10_Wörterbuch"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

print("="*80)
print("WÖRTERBUCH GENERATOR - INDICATOR ENCYCLOPEDIA")
print("="*80)

# Load Matrix Ranges
matrix_file = LAZORA_PATH / "MATRIX_RANGES_COMPLETE.json"
with open(matrix_file, 'r', encoding='utf-8') as f:
    matrix_data = json.load(f)

print(f"\nLoaded {len(matrix_data)} indicators")

# Generate Wörterbuch entries
woerterbuch = []

for ind in matrix_data:
    entry = {
        'ID': ind['Indicator_Num'],
        'Name': ind['Indicator_Name'],
        'Dimensionality': ind['Dimensionality'],
        'Parameters': {},
        'Matrix_Info': {
            'Entry_Combinations': ind['Entry_Combinations'],
            'Exit_Combinations': ind['Exit_Combinations'],
            'Total_Combinations': ind['Total_Combinations'],
            'Lazora_Phase1_Samples': ind['Lazora_Phase1_Samples'],
            'Efficiency_Percent': round(ind['Efficiency_Ratio'] * 100, 4)
        }
    }
    
    # Entry Parameters
    for param_name, param_info in ind['Entry_Matrix'].items():
        entry['Parameters'][param_name] = {
            'Type': param_info['type'],
            'Default': param_info['default'],
            'Min': param_info['min'],
            'Max': param_info['max'],
            'Steps': param_info['steps'],
            'Category': 'Entry'
        }
    
    # Exit Parameters
    for param_name, param_info in ind['Exit_Matrix'].items():
        entry['Parameters'][param_name] = {
            'Type': 'int',
            'Min': param_info['min'],
            'Max': param_info['max'],
            'Steps': param_info['steps'],
            'Category': 'Exit'
        }
    
    woerterbuch.append(entry)
    
    print(f"\r[{ind['Indicator_Num']:03d}] {ind['Indicator_Name'][:50]:50s}", end='', flush=True)

print("\n\nWörterbuch generation complete!")

# Save as JSON
json_file = OUTPUT_PATH / "INDICATOR_ENCYCLOPEDIA.json"
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(woerterbuch, f, indent=2)

print(f"JSON: {json_file}")

# Save as CSV (flattened)
csv_data = []
for entry in woerterbuch:
    row = {
        'ID': entry['ID'],
        'Name': entry['Name'],
        'Dimensionality': entry['Dimensionality'],
        'Total_Combinations': entry['Matrix_Info']['Total_Combinations'],
        'Phase1_Samples': entry['Matrix_Info']['Lazora_Phase1_Samples'],
        'Efficiency_%': entry['Matrix_Info']['Efficiency_Percent']
    }
    
    # Add parameters
    for param_name, param_info in entry['Parameters'].items():
        prefix = param_name.upper()
        row[f'{prefix}_Type'] = param_info['Type']
        row[f'{prefix}_Default'] = param_info.get('Default', 'N/A')
        row[f'{prefix}_Min'] = param_info['Min']
        row[f'{prefix}_Max'] = param_info['Max']
        row[f'{prefix}_Steps'] = param_info['Steps']
        row[f'{prefix}_Category'] = param_info['Category']
    
    csv_data.append(row)

df = pd.DataFrame(csv_data)
csv_file = OUTPUT_PATH / "INDICATOR_ENCYCLOPEDIA.csv"
df.to_csv(csv_file, index=False)

print(f"CSV: {csv_file}")

# Generate readable summary
summary_lines = []
summary_lines.append("="*80)
summary_lines.append("INDICATOR ENCYCLOPEDIA - SUMMARY")
summary_lines.append("="*80)
summary_lines.append("")

for entry in woerterbuch[:10]:  # First 10 as example
    summary_lines.append(f"[{entry['ID']:03d}] {entry['Name']}")
    summary_lines.append(f"  Dimensionality: {entry['Dimensionality']}D")
    summary_lines.append(f"  Total Combinations: {entry['Matrix_Info']['Total_Combinations']:,}")
    summary_lines.append(f"  Lazora Phase 1: {entry['Matrix_Info']['Lazora_Phase1_Samples']} samples")
    summary_lines.append(f"  Efficiency: {entry['Matrix_Info']['Efficiency_Percent']:.4f}%")
    summary_lines.append("  Parameters:")
    
    for param_name, param_info in entry['Parameters'].items():
        if param_info['Category'] == 'Entry':
            default_str = f" (Default: {param_info['Default']})" if 'Default' in param_info else ""
            summary_lines.append(f"    - {param_name}: [{param_info['Min']}, {param_info['Max']}]{default_str}")
    
    summary_lines.append("")

summary_lines.append("... (592 total indicators)")
summary_lines.append("")
summary_lines.append("="*80)

summary_file = OUTPUT_PATH / "ENCYCLOPEDIA_SUMMARY.txt"
with open(summary_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(summary_lines))

print(f"Summary: {summary_file}")

print("\n" + "="*80)
print("WÖRTERBUCH COMPLETE!")
print("="*80)
print(f"Total Indicators: {len(woerterbuch)}")
print(f"Files generated: 3 (JSON, CSV, TXT)")
print("="*80)
