import pandas as pd
import numpy as np
from pathlib import Path
import json

# Validiere alle abgeschlossenen CSV Dateien
CSV_PATH = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\Fixed_Exit\1h")

# SUCCESS Indikatoren (92 original + neue)
success_inds = [4, 9, 2, 7, 6, 1, 5, 11, 10, 3, 12, 33, 27, 15, 34, 37, 36, 38, 39, 40, 42, 41, 46, 51, 50, 53, 49, 52, 63, 62, 60, 61, 64, 48, 67, 47, 65, 66, 68, 73, 78, 75, 79, 85, 80, 69, 99, 98, 87, 100, 104, 96, 105, 118, 121, 108, 122, 123, 145, 156, 155, 151, 153, 165, 170, 186, 195, 191, 212, 207, 221, 179, 263, 255, 271, 276, 291, 289, 299, 296, 273, 305, 316, 323, 326, 349, 355, 357, 362]

csv_files = [f for f in CSV_PATH.glob("*.csv") if any(f.name.startswith(f"{i:03d}_") for i in success_inds)]

print(f"Validating {len(csv_files)} CSV files...")
print("="*80)

validation_results = {
    'total_files': len(csv_files),
    'valid': [],
    'issues': []
}

for csv_file in csv_files:
    try:
        df = pd.read_csv(csv_file)
        
        # Required columns
        required_cols = ['Total_Return', 'Max_Drawdown', 'Daily_Drawdown', 'Win_Rate_%', 
                        'Total_Trades', 'Profit_Factor', 'Sharpe_Ratio', 'Net_Profit']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            validation_results['issues'].append({
                'file': csv_file.name,
                'error': f'Missing columns: {missing_cols}'
            })
            continue
        
        # Validate metrics
        issues = []
        
        # 1. Drawdown should be <= 0 or positive (depends on convention)
        if df['Max_Drawdown'].min() < 0:
            issues.append('Max_Drawdown has negative values')
        
        # 2. Win Rate should be 0-100
        if (df['Win_Rate_%'] < 0).any() or (df['Win_Rate_%'] > 100).any():
            issues.append('Win_Rate_% outside 0-100 range')
        
        # 3. Total Trades should be positive
        if (df['Total_Trades'] <= 0).any():
            issues.append('Total_Trades has zero or negative values')
        
        # 4. Profit Factor should be positive
        if (df['Profit_Factor'] < 0).any():
            issues.append('Profit_Factor has negative values')
        
        # 5. Check for NaN values
        nan_cols = df[required_cols].columns[df[required_cols].isna().any()].tolist()
        if nan_cols:
            issues.append(f'NaN values in: {nan_cols}')
        
        # 6. Validate Return calculation (Net_Profit should match Total_Return * initial_capital)
        # Assuming initial capital = 10000
        expected_net_profit = df['Total_Return'] * 10000
        profit_diff = abs(df['Net_Profit'] - expected_net_profit)
        if (profit_diff > 1).any():  # Allow 1 unit tolerance
            issues.append('Net_Profit does not match Total_Return calculation')
        
        if issues:
            validation_results['issues'].append({
                'file': csv_file.name,
                'issues': issues,
                'sample_data': {
                    'Total_Return': [float(df['Total_Return'].min()), float(df['Total_Return'].max())],
                    'Max_Drawdown': [float(df['Max_Drawdown'].min()), float(df['Max_Drawdown'].max())],
                    'Profit_Factor': [float(df['Profit_Factor'].min()), float(df['Profit_Factor'].max())],
                    'Sharpe_Ratio': [float(df['Sharpe_Ratio'].min()), float(df['Sharpe_Ratio'].max())]
                }
            })
        else:
            validation_results['valid'].append({
                'file': csv_file.name,
                'rows': len(df),
                'best_sharpe': float(df['Sharpe_Ratio'].max()),
                'best_pf': float(df['Profit_Factor'].max()),
                'best_return': float(df['Total_Return'].max())
            })
    
    except Exception as e:
        validation_results['issues'].append({
            'file': csv_file.name,
            'error': f'Failed to read: {str(e)}'
        })

# Summary
print(f"\n{'='*80}")
print(f"VALIDATION SUMMARY")
print(f"{'='*80}")
print(f"Total Files: {validation_results['total_files']}")
print(f"Valid Files: {len(validation_results['valid'])}")
print(f"Files with Issues: {len(validation_results['issues'])}")
print(f"{'='*80}\n")

if validation_results['valid']:
    print(f"✅ VALID FILES ({len(validation_results['valid'])}):")
    for item in sorted(validation_results['valid'], key=lambda x: x['best_sharpe'], reverse=True)[:10]:
        print(f"  {item['file'][:30]:30s} | Rows: {item['rows']:4d} | Best SR: {item['best_sharpe']:6.2f} | Best PF: {item['best_pf']:5.2f} | Best Return: {item['best_return']:7.2%}")

if validation_results['issues']:
    print(f"\n⚠️ FILES WITH ISSUES ({len(validation_results['issues'])}):")
    for item in validation_results['issues'][:10]:
        print(f"  {item['file']}")
        if 'issues' in item:
            for issue in item['issues']:
                print(f"    - {issue}")
        if 'error' in item:
            print(f"    - {item['error']}")

# Save results
output_file = Path(r"/opt/Zenatus_Backtester\01_Backtest_System\CSV_VALIDATION_RESULTS.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(validation_results, f, indent=2)

print(f"\n✅ Validation results saved to: {output_file}")
