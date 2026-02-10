# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import os
from pathlib import Path
import json

# CONFIG
RESULTS_DIR = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h")
DOC_DIR = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h/QualityCheck")
TOP_1000_DIR = RESULTS_DIR  # Save directly in results folder as requested

def analyze_results():
    print("=== STARTING ANALYSIS ===")
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    
    files = sorted(list(RESULTS_DIR.glob("*.csv")))
    print(f"Found {len(files)} CSV files.")
    
    # QC Storage
    qc_empty_files = []
    qc_no_results = []
    qc_nan_params = []
    
    # Ranking Storage (Dictionary of lists)
    # Key: Symbol, Value: List of dicts (rows)
    best_per_symbol = {}
    
    for i, fpath in enumerate(files):
        if "TOP1000" in fpath.name: continue
        
        try:
            # Read CSV
            df = pd.read_csv(fpath)
            
            # 1. Check Empty File
            if len(df) == 0:
                qc_empty_files.append(fpath.name)
                print(f"[QC] Empty file: {fpath.name}")
                continue
                
            # 2. Check "0 Results" / No Trades
            # Assuming if Total_Trades is 0 or NaN, it's a "no result" case effectively
            # Or if the file exists but has no valid rows
            if "Total_Trades" in df.columns:
                zero_trades = df[df["Total_Trades"] == 0]
                if len(zero_trades) == len(df):
                    qc_no_results.append(fpath.name)
                    # We might still process it, but usually these have 0 return
            
            # 3. Check NaN Parameters
            # Identify parameter columns
            param_cols = [c for c in df.columns if "Parameter" in c]
            if param_cols:
                # Check if ALL parameter columns are NaN for ALL rows
                # (Strategies that failed to pass params correctly)
                # We check if any row has valid params. 
                # If all rows have all NaNs in param cols -> Flag
                if df[param_cols].isna().all().all():
                    qc_nan_params.append(fpath.name)
                    print(f"[QC] NaN Parameters: {fpath.name}")
            
            # 4. Process for Top 1000
            # Required columns
            req_cols = ["Symbol", "Total_Return", "Max_Drawdown", "Total_Trades"]
            if not all(c in df.columns for c in req_cols):
                continue
                
            # Calculate Metric: Return / MaxDD
            # Handle Zero Division: If MaxDD is 0...
            # If Return > 0 and DD = 0 -> Infinite (Perfect score) -> Replace DD with 0.001
            # If Return <= 0 and DD = 0 -> Bad score
            
            # Vectorized calculation
            # Avoid SettingWithCopyWarning by working on a copy or directly
            # Create a working copy of relevant columns to save memory
            
            keep_cols = ["Indicator", "Symbol", "Total_Return", "Max_Drawdown", "Total_Trades", "Win_Rate_%", "Profit_Factor"] + param_cols
            # Filter cols that exist
            keep_cols = [c for c in keep_cols if c in df.columns]
            
            # Filter for positive return (optional, but "Top" implies good)
            # User asked for "Top 1000... nach verhältniss". Even negative ones have a ratio.
            # But usually we only care about positive returns.
            # Let's keep everything but sort correctly.
            
            df_calc = df[keep_cols].copy()
            
            # Convert to numeric just in case
            df_calc["Total_Return"] = pd.to_numeric(df_calc["Total_Return"], errors='coerce').fillna(-999)
            df_calc["Max_Drawdown"] = pd.to_numeric(df_calc["Max_Drawdown"], errors='coerce').fillna(100) # Penalize NaN DD
            
            # Ratio Logic
            # We want High Return, Low DD.
            # If DD is 0, we treat it as 0.1 to avoid Inf, but still very high rank.
            
            conditions = [
                (df_calc["Max_Drawdown"] <= 0.001) & (df_calc["Total_Return"] > 0),
                (df_calc["Max_Drawdown"] <= 0.001) & (df_calc["Total_Return"] <= 0),
                (df_calc["Max_Drawdown"] > 0.001)
            ]
            choices = [
                df_calc["Total_Return"] * 1000, # Boost score for 0 DD
                df_calc["Total_Return"],        # Neutral/Bad
                df_calc["Total_Return"] / df_calc["Max_Drawdown"]
            ]
            
            df_calc["Score"] = np.select(conditions, choices, default=-999)
            
            # Iterate Symbols in this file
            grouped = df_calc.groupby("Symbol")
            for symbol, group in grouped:
                if symbol not in best_per_symbol:
                    best_per_symbol[symbol] = []
                
                # Convert to dict (records) and add
                # We only need to keep the best 1000 "so far" to save memory
                
                # Optimize: Get top 1000 of this group first
                top_group = group.nlargest(1000, "Score")
                best_per_symbol[symbol].extend(top_group.to_dict('records'))
                
                # Prune if too large (e.g. > 2000)
                if len(best_per_symbol[symbol]) > 2000:
                    temp_df = pd.DataFrame(best_per_symbol[symbol])
                    best_per_symbol[symbol] = temp_df.nlargest(1000, "Score").to_dict('records')

        except Exception as e:
            print(f"[ERR] Processing {fpath.name}: {e}")
            
        if (i+1) % 50 == 0:
            print(f"Processed {i+1}/{len(files)} files...")

    # Final Pruning and Saving Top 1000
    print("=== SAVING RESULTS ===")
    
    for symbol, rows in best_per_symbol.items():
        if not rows: continue
        
        final_df = pd.DataFrame(rows)
        # Sort desc
        final_df = final_df.sort_values("Score", ascending=False).head(1000)
        
        # Drop Score column if user didn't ask for it? Or keep it as "Ret_DD_Ratio"?
        final_df.rename(columns={"Score": "Ret_DD_Ratio"}, inplace=True)
        
        # Save
        out_name = f"0_TOP1000_{symbol}.csv"
        out_path = TOP_1000_DIR / out_name
        final_df.to_csv(out_path, index=False)
        print(f"Saved {out_name} ({len(final_df)} rows)")

    # Save QC Report
    with open(DOC_DIR / "qc_report.txt", "w") as f:
        f.write("=== QUALITY CHECK REPORT ===\n")
        f.write(f"Scanned {len(files)} files.\n\n")
        
        f.write(f"--- EMPTY FILES ({len(qc_empty_files)}) ---\n")
        for x in qc_empty_files: f.write(f"{x}\n")
        f.write("\n")
        
        f.write(f"--- NO RESULTS / ZERO TRADES ({len(qc_no_results)}) ---\n")
        for x in qc_no_results: f.write(f"{x}\n")
        f.write("\n")
        
        f.write(f"--- NAN PARAMETERS ({len(qc_nan_params)}) ---\n")
        for x in qc_nan_params: f.write(f"{x}\n")
        f.write("\n")
        
    print("QC Report saved.")

if __name__ == "__main__":
    analyze_results()
