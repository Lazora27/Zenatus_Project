# -*- coding: utf-8 -*-
"""
TOP 1000 GENERATOR - POST-BACKTEST ANALYSIS
============================================
Erstellt Top 1000 Listen nach Sharpe Ratio und Profit Factor
PRO SYMBOL + GESAMT
"""

import sys
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

BASE_PATH = Path(r"D:\2_Trading\Superindikator_Alpha")
BACKTEST_PATH = BASE_PATH / "01_Backtest_System" / "Documentation" / "Fixed_Exit"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System" / "Top_1000_Rankings"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
TIMEFRAMES = ['1h', '30m', '15m', '5m']

print("="*80)
print("TOP 1000 GENERATOR - SHARPE RATIO & PROFIT FACTOR")
print("="*80)

def generate_top_1000(timeframe='1h'):
    """Generate Top 1000 rankings for one timeframe"""
    
    print(f"\nProcessing: {timeframe.upper()}")
    
    tf_path = BACKTEST_PATH / timeframe
    
    if not tf_path.exists():
        print(f"[SKIP] No data for {timeframe}")
        return
    
    # Collect all results
    all_results = []
    
    csv_files = sorted(tf_path.glob("*.csv"))
    print(f"Found {len(csv_files)} indicator files")
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            # Only use FULL phase (100% data)
            df_full = df[df['Phase'] == 'FULL'].copy()
            
            all_results.append(df_full)
            
        except Exception as e:
            print(f"[ERROR] {csv_file.name}: {str(e)[:30]}")
            continue
    
    if len(all_results) == 0:
        print("[SKIP] No results found")
        return
    
    # Combine all
    df_all = pd.concat(all_results, ignore_index=True)
    
    print(f"Total rows: {len(df_all):,}")
    
    # === PER SYMBOL TOP 1000 ===
    
    for symbol in SYMBOLS:
        df_symbol = df_all[df_all['Symbol'] == symbol].copy()
        
        if len(df_symbol) == 0:
            continue
        
        # Sort by Sharpe Ratio
        df_sharpe = df_symbol.sort_values('Sharpe_Ratio', ascending=False).head(1000).copy()
        df_sharpe['Rank'] = range(1, len(df_sharpe) + 1)
        
        output_file = OUTPUT_PATH / timeframe / f"{symbol}_TOP1000_SHARPE.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df_sharpe.to_csv(output_file, index=False, float_format='%.6f')
        
        # Sort by Profit Factor
        df_pf = df_symbol.sort_values('Profit_Factor', ascending=False).head(1000).copy()
        df_pf['Rank'] = range(1, len(df_pf) + 1)
        
        output_file = OUTPUT_PATH / timeframe / f"{symbol}_TOP1000_PF.csv"
        df_pf.to_csv(output_file, index=False, float_format='%.6f')
        
        print(f"  {symbol}: Top1000 Sharpe & PF saved")
    
    # === OVERALL TOP 1000 (All Symbols) ===
    
    # Sharpe Ratio
    df_sharpe_all = df_all.sort_values('Sharpe_Ratio', ascending=False).head(1000).copy()
    df_sharpe_all['Rank'] = range(1, len(df_sharpe_all) + 1)
    
    output_file = OUTPUT_PATH / timeframe / f"ALL_SYMBOLS_TOP1000_SHARPE.csv"
    df_sharpe_all.to_csv(output_file, index=False, float_format='%.6f')
    
    # Profit Factor
    df_pf_all = df_all.sort_values('Profit_Factor', ascending=False).head(1000).copy()
    df_pf_all['Rank'] = range(1, len(df_pf_all) + 1)
    
    output_file = OUTPUT_PATH / timeframe / f"ALL_SYMBOLS_TOP1000_PF.csv"
    df_pf_all.to_csv(output_file, index=False, float_format='%.6f')
    
    print(f"  ALL_SYMBOLS: Top1000 Sharpe & PF saved")
    
    # === SUMMARY ===
    
    summary = {
        'Timeframe': timeframe,
        'Total_Rows': len(df_all),
        'Top1_Sharpe': f"{df_sharpe_all.iloc[0]['Indicator']} ({df_sharpe_all.iloc[0]['Sharpe_Ratio']:.2f})",
        'Top1_PF': f"{df_pf_all.iloc[0]['Indicator']} ({df_pf_all.iloc[0]['Profit_Factor']:.2f})",
        'Files_Created': 14  # 6 symbols × 2 + 2 all_symbols
    }
    
    return summary

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        timeframe = sys.argv[1]
        generate_top_1000(timeframe)
    else:
        # Generate for all timeframes
        summaries = []
        for tf in TIMEFRAMES:
            summary = generate_top_1000(tf)
            if summary:
                summaries.append(summary)
        
        # Final Summary
        print("\n" + "="*80)
        print("TOP 1000 GENERATION COMPLETE!")
        print("="*80)
        
        for s in summaries:
            print(f"\n{s['Timeframe'].upper()}:")
            print(f"  Total Rows: {s['Total_Rows']:,}")
            print(f"  Top Sharpe: {s['Top1_Sharpe']}")
            print(f"  Top PF: {s['Top1_PF']}")
            print(f"  Files: {s['Files_Created']}")
        
        total_files = sum([s['Files_Created'] for s in summaries])
        print(f"\n{'='*80}")
        print(f"TOTAL FILES CREATED: {total_files}")
        print(f"  Per Symbol: {len(SYMBOLS)} × 2 × 4 TF = {len(SYMBOLS)*2*4}")
        print(f"  All Symbols: 2 × 4 TF = {2*4}")
        print(f"{'='*80}")
        
        print(f"\nLocation: {OUTPUT_PATH}/")
