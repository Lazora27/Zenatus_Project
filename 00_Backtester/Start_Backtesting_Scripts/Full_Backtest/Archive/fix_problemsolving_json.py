import json
from pathlib import Path

base = Path(r"/opt/Zenatus_Dokumentation\Dokumentation")
problem_json = json.load(open(base / 'INDICATORS_PROBLEMSOLVING.json'))

fixed_json = {}

for ind_id, ind_data in problem_json.items():
    fixed_json[ind_id] = ind_data.copy()
    fixed_json[ind_id]['optimal_inputs'] = {}
    
    for param_name, param_data in ind_data['optimal_inputs'].items():
        fixed_json[ind_id]['optimal_inputs'][param_name] = param_data.copy()
        
        if 'values' in param_data and isinstance(param_data['values'], list):
            new_values = []
            for v in param_data['values']:
                if isinstance(v, float) and v == int(v):
                    new_values.append(int(v))
                else:
                    new_values.append(v)
            fixed_json[ind_id]['optimal_inputs'][param_name]['values'] = new_values

json.dump(fixed_json, open(base / 'INDICATORS_PROBLEMSOLVING_FIXED.json', 'w'), indent=2)
print(f'Created INDICATORS_PROBLEMSOLVING_FIXED.json with Float->Int conversion for {len(fixed_json)} indicators')
