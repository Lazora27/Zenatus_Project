# -*- coding: utf-8 -*-
"""
HEATMAP VISUALIZER - LAZORA PHASE 1
====================================
Generates heatmaps from backtest results
2D-4D: Standard plots
5D+: t-SNE dimensionality reduction
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import json
import warnings
warnings.filterwarnings('ignore')

BASE_PATH = Path(r"D:\2_Trading\Superindikator_Alpha")
HEATMAP_DATA_PATH = BASE_PATH / "08_Heatmaps" / "Fixed_Exit"
LAZORA_PATH = BASE_PATH / "08_Lazora_Verfahren"

print("="*80)
print("HEATMAP VISUALIZER - LAZORA PHASE 1")
print("="*80)

# Load Matrix Info (INTELLIGENT VERSION!)
matrix_file = LAZORA_PATH / "PARAMETER_HANDBOOK_INTELLIGENT.json"
if not matrix_file.exists():
    print("[WARNING] Intelligent handbook not found, trying standard...")
    matrix_file = BASE_PATH / "01_Backtest_System" / "Parameter_Optimization" / "PARAMETER_HANDBOOK_COMPLETE.json"

with open(matrix_file, 'r', encoding='utf-8') as f:
    handbook = json.load(f)
    MATRIX_DATA = {}
    for ind in handbook:
        ind_num = ind['Indicator_Num']
        entry_matrix = {}
        for param_name, param_config in ind['Entry_Params'].items():
            entry_matrix[param_name] = {
                'min': min(param_config['values']) if 'values' in param_config else param_config.get('start', 0),
                'max': max(param_config['values']) if 'values' in param_config else param_config.get('end', 100),
                'steps': len(param_config['values']) if 'values' in param_config else param_config.get('num_steps', 20)
            }
        
        MATRIX_DATA[ind_num] = {
            'Indicator_Num': ind_num,
            'Indicator_Name': ind['Indicator_Name'],
            'Entry_Matrix': entry_matrix,
            'Total_Combinations': ind.get('Total_Combinations', 0),
            'Dimensionality': len(entry_matrix)
        }

def generate_heatmap(ind_num, ind_name, timeframe='1h'):
    """Generate heatmap for one indicator"""
    
    heatmap_file = HEATMAP_DATA_PATH / timeframe / f"{ind_num:03d}_{ind_name}_heatmap_data.csv"
    
    if not heatmap_file.exists():
        print(f"[SKIP] {ind_num:03d} - no heatmap data")
        return None
    
    # Load data
    df = pd.read_csv(heatmap_file)
    
    if len(df) == 0:
        return None
    
    # Get dimensionality
    matrix = MATRIX_DATA.get(ind_num, {})
    entry_params = matrix.get('Entry_Matrix', {})
    n_dims = len(entry_params)
    
    # Determine plot type
    if n_dims == 0:
        # Only TP/SL, 2D plot
        fig, ax = plt.subplots(figsize=(10, 8))
        scatter = ax.scatter(df['TP_Pips'], df['SL_Pips'], 
                           c=df['Sharpe_Ratio'], 
                           cmap='RdYlGn', 
                           s=50, 
                           alpha=0.6,
                           vmin=-1, vmax=3)
        ax.set_xlabel('TP Pips')
        ax.set_ylabel('SL Pips')
        ax.set_title(f'{ind_num:03d} {ind_name} - Sharpe Ratio Heatmap')
        plt.colorbar(scatter, label='Sharpe Ratio')
        
    elif n_dims == 1:
        # 1 param + TP/SL, show param vs Sharpe
        param_name = list(entry_params.keys())[0]
        fig, ax = plt.subplots(figsize=(10, 8))
        scatter = ax.scatter(df[param_name], df['Sharpe_Ratio'], 
                           c=df['Total_Return'], 
                           cmap='RdYlGn', 
                           s=50, 
                           alpha=0.6)
        ax.set_xlabel(param_name)
        ax.set_ylabel('Sharpe Ratio')
        ax.set_title(f'{ind_num:03d} {ind_name} - Parameter Optimization')
        plt.colorbar(scatter, label='Return %')
        
    elif n_dims == 2:
        # 2D scatter
        param_names = list(entry_params.keys())
        fig, ax = plt.subplots(figsize=(10, 8))
        scatter = ax.scatter(df[param_names[0]], df[param_names[1]], 
                           c=df['Sharpe_Ratio'], 
                           cmap='RdYlGn', 
                           s=50, 
                           alpha=0.6,
                           vmin=-1, vmax=3)
        ax.set_xlabel(param_names[0])
        ax.set_ylabel(param_names[1])
        ax.set_title(f'{ind_num:03d} {ind_name} - {n_dims}D Heatmap')
        plt.colorbar(scatter, label='Sharpe Ratio')
        
    elif n_dims == 3:
        # 3D scatter
        param_names = list(entry_params.keys())
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(df[param_names[0]], df[param_names[1]], df[param_names[2]],
                           c=df['Sharpe_Ratio'], 
                           cmap='RdYlGn', 
                           s=30, 
                           alpha=0.6,
                           vmin=-1, vmax=3)
        ax.set_xlabel(param_names[0])
        ax.set_ylabel(param_names[1])
        ax.set_zlabel(param_names[2])
        ax.set_title(f'{ind_num:03d} {ind_name} - {n_dims}D Heatmap')
        plt.colorbar(scatter, label='Sharpe Ratio')
        
    else:
        # High-dimensional: Use t-SNE
        param_names = list(entry_params.keys())
        param_values = df[param_names].values
        
        if len(param_values) < 30:
            print(f"[SKIP] {ind_num:03d} - too few samples for t-SNE")
            return None
        
        # t-SNE to 3D
        tsne = TSNE(n_components=3, perplexity=min(30, len(param_values)//2), n_iter=1000, random_state=42)
        coords_3d = tsne.fit_transform(param_values)
        
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(coords_3d[:, 0], coords_3d[:, 1], coords_3d[:, 2],
                           c=df['Sharpe_Ratio'], 
                           cmap='RdYlGn', 
                           s=30, 
                           alpha=0.6,
                           vmin=-1, vmax=3)
        ax.set_xlabel('t-SNE 1')
        ax.set_ylabel('t-SNE 2')
        ax.set_zlabel('t-SNE 3')
        ax.set_title(f'{ind_num:03d} {ind_name} - {n_dims}D Heatmap (t-SNE)')
        plt.colorbar(scatter, label='Sharpe Ratio')
        
        # Add text: Matrix info
        info_text = f"Dimensionality: {n_dims}D\n"
        info_text += f"Total Combos: {matrix.get('Total_Combinations', 0):,}\n"
        info_text += f"Phase 1 Samples: {len(df)}\n"
        info_text += f"Parameters: {', '.join(param_names)}"
        fig.text(0.02, 0.02, info_text, fontsize=8, family='monospace', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Save
    output_file = HEATMAP_DATA_PATH / timeframe / f"{ind_num:03d}_{ind_name}_heatmap.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_file

def generate_all_heatmaps(timeframe='1h'):
    """Generate heatmaps for all indicators in timeframe"""
    heatmap_data_dir = HEATMAP_DATA_PATH / timeframe
    heatmap_files = sorted(heatmap_data_dir.glob("*_heatmap_data.csv"))
    
    print(f"\nGenerating heatmaps for {len(heatmap_files)} indicators...")
    
    success_count = 0
    for i, heatmap_file in enumerate(heatmap_files, 1):
        ind_name = heatmap_file.stem.replace('_heatmap_data', '')
        try:
            ind_num = int(ind_name.split('_')[0])
        except:
            continue
        
        print(f"\r[{i}/{len(heatmap_files)}] {ind_name[:50]:50s}", end='', flush=True)
        
        try:
            result = generate_heatmap(ind_num, ind_name, timeframe)
            if result:
                success_count += 1
        except Exception as e:
            print(f"\n[ERROR] {ind_name}: {str(e)[:50]}")
    
    print(f"\n\nHeatmaps generated: {success_count}/{len(heatmap_files)}")
    print(f"Location: 08_Heatmaps/Fixed_Exit/{timeframe}/")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        timeframe = sys.argv[1]
    else:
        timeframe = '1h'
    
    print(f"\nTimeframe: {timeframe}")
    generate_all_heatmaps(timeframe)
    
    print("\n" + "="*80)
    print("HEATMAP GENERATION COMPLETE!")
    print("="*80)
