"""
Finde und analysiere KOMPLEXE Indikatoren (>2 Parameter)
"""
import json
from pathlib import Path

analysis_file = Path("DEEP_PARAMETER_ANALYSIS_SAMPLE.json")

with open(analysis_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Finde komplexe Indikatoren
complex_indicators = {}
for ind_num, ind_data in data.items():
    num_params = len(ind_data['parameters'])
    if num_params > 2:
        complex_indicators[ind_num] = ind_data

print("="*80)
print(f"KOMPLEXE INDIKATOREN (>2 Parameter): {len(complex_indicators)}")
print("="*80)

# Sortiere nach Kombinationen
sorted_complex = sorted(complex_indicators.items(), 
                       key=lambda x: x[1]['total_combinations'], 
                       reverse=True)

for ind_num, ind_data in sorted_complex[:30]:
    name = ind_data['name']
    params = ind_data['parameters']
    combos = ind_data['total_combinations']
    
    print(f"\n#{ind_num}: {name}")
    print(f"  Parameter: {len(params)}")
    for param_name, param_config in params.items():
        values = param_config['values']
        range_info = param_config['range']
        print(f"    {param_name}: {len(values)} values ({range_info['start']} - {range_info['end']})")
    print(f"  Total Kombinationen: {combos}")

print(f"\n{'='*80}")
print("TOP KOMPLEXE INDIKATOREN IDENTIFIZIERT")
print(f"{'='*80}")
