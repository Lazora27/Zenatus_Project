"""
Extrahiert alle Kombinationen mit Sharpe Ratio >= 2.0 aus alten CSV-Files
und speichert sie im OP-Ordner
"""
import pandas as pd
from pathlib import Path
import glob

# Pfade
OLD_CSVS_PATH = Path(r"/opt/Zenatus_Backtester\03_Archive\Old_Backtests\11_Backtest_Neuster_Stand")
OP_PATH = Path(r"/opt/Zenatus_Backtester\01_Backtest_System\Documentation\Fixed_Exit\OP")

print("="*80)
print("EXTRAHIERE SHARPE RATIO >= 2.0 KOMBINATIONEN")
print("="*80)

# Finde alle CSV-Files
csv_files = list(OLD_CSVS_PATH.glob("*.csv"))
print(f"\nGefunden: {len(csv_files)} CSV-Files")

all_sr2_combos = []
total_rows = 0
sr2_count = 0

for csv_file in csv_files:
    try:
        df = pd.read_csv(csv_file)
        total_rows += len(df)
        
        # Suche nach Sharpe Ratio Spalte (verschiedene mögliche Namen)
        sr_col = None
        for col in df.columns:
            if 'sharpe' in col.lower() or 'sr' in col.lower():
                sr_col = col
                break
        
        if sr_col is None:
            continue
        
        # Filtere SR >= 2.0
        df_filtered = df[df[sr_col] >= 2.0].copy()
        
        if len(df_filtered) > 0:
            sr2_count += len(df_filtered)
            all_sr2_combos.append(df_filtered)
            print(f"✓ {csv_file.name}: {len(df_filtered)} Kombinationen mit SR>=2.0")
    
    except Exception as e:
        print(f"✗ {csv_file.name}: Fehler - {str(e)[:50]}")
        continue

print(f"\n{'='*80}")
print(f"ZUSAMMENFASSUNG:")
print(f"{'='*80}")
print(f"Total Rows gescannt: {total_rows:,}")
print(f"SR >= 2.0 gefunden: {sr2_count:,}")
print(f"Prozentsatz: {(sr2_count/total_rows*100) if total_rows > 0 else 0:.2f}%")

if all_sr2_combos:
    # Kombiniere alle Daten
    df_combined = pd.concat(all_sr2_combos, ignore_index=True)
    
    # Sortiere nach Sharpe Ratio (absteigend)
    sr_col = None
    for col in df_combined.columns:
        if 'sharpe' in col.lower() or 'sr' in col.lower():
            sr_col = col
            break
    
    if sr_col:
        df_combined = df_combined.sort_values(by=sr_col, ascending=False)
    
    # Speichere
    output_file = OP_PATH / "ALL_SR2_PLUS_COMBINATIONS.csv"
    df_combined.to_csv(output_file, index=False)
    print(f"\n✓ Gespeichert: {output_file}")
    print(f"  Zeilen: {len(df_combined):,}")
    
    # Zeige Top 10
    print(f"\n{'='*80}")
    print("TOP 10 SHARPE RATIOS:")
    print(f"{'='*80}")
    if sr_col:
        for i, (idx, row) in enumerate(df_combined.head(10).iterrows(), 1):
            indicator = str(row.get('Indicator', row.get('EA_Name', 'Unknown')))
            symbol = str(row.get('Symbol', 'Unknown'))
            sr = row[sr_col]
            pf = row.get('Profit_Factor', row.get('PF', 'N/A'))
            print(f"{i:2d}. {indicator[:40]:40s} | {symbol:8s} | SR={sr:.2f} | PF={pf}")
else:
    print("\n✗ Keine Kombinationen mit SR >= 2.0 gefunden!")

print(f"\n{'='*80}")
print("FERTIG!")
print(f"{'='*80}")
