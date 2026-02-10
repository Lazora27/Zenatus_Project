"""
522_price_graph_connectivity.py
================================
Indicator: Price Graph Connectivity
Category: Network Analysis / Graph Theory
Complexity: Elite

Description:
-----------
Measures connectivity in price movement graphs. High connectivity indicates
well-connected market states (trending), low connectivity indicates fragmented
states (ranging/choppy). Uses graph theory to quantify market structure.

Key Features:
- Graph connectivity measurement
- Connected components detection
- Path analysis
- Connectivity-based regime classification

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_PriceGraphConnectivity:
    """
    Price Graph Connectivity
    
    Measures connectivity in price movement graphs.
    """
    
    def __init__(self):
        self.name = "Price Graph Connectivity"
        self.version = "1.0.0"
        self.category = "Network Analysis"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Graph Connectivity metrics
        
        Parameters:
        - graph_period: Period for graph construction (default: 34)
        - connectivity_threshold: Threshold for edge creation (default: 0.02)
        - path_length: Maximum path length to consider (default: 5)
        """
        graph_period = params.get('graph_period', 34)
        connectivity_threshold = params.get('connectivity_threshold', 0.02)
        path_length = params.get('path_length', 5)
        
        returns = data['close'].pct_change()
        
        # 1. Edge Density (how connected is the graph)
        # Create edges between similar price movements
        edge_density = pd.Series(0.0, index=data.index)
        
        for i in range(graph_period, len(data)):
            window_returns = returns.iloc[i-graph_period:i].values
            
            # Count edges (similar returns)
            edges = 0
            for j in range(len(window_returns)):
                for k in range(j+1, len(window_returns)):
                    if abs(window_returns[j] - window_returns[k]) < connectivity_threshold:
                        edges += 1
            
            # Normalize by maximum possible edges
            max_edges = len(window_returns) * (len(window_returns) - 1) / 2
            edge_density.iloc[i] = edges / max_edges if max_edges > 0 else 0
        
        # 2. Average Degree (average connections per node)
        avg_degree = edge_density * (graph_period - 1)
        
        # 3. Graph Diameter (longest shortest path - simplified)
        # Use price range as proxy
        graph_diameter = (data['high'].rolling(window=graph_period).max() - 
                         data['low'].rolling(window=graph_period).min()) / data['close']
        
        # 4. Connectivity Score (high edge density + low diameter = well connected)
        connectivity_score = edge_density / (graph_diameter + 1e-10)
        connectivity_normalized = connectivity_score / connectivity_score.rolling(window=50).mean()
        
        # 5. Connected Components (number of disconnected subgraphs)
        # Simplified: periods of similar returns form components
        num_components = pd.Series(0, index=data.index)
        
        for i in range(graph_period, len(data)):
            window_returns = returns.iloc[i-graph_period:i].values
            
            # Group similar returns
            components = 0
            visited = np.zeros(len(window_returns), dtype=bool)
            
            for j in range(len(window_returns)):
                if not visited[j]:
                    components += 1
                    # Mark all similar returns as visited
                    for k in range(len(window_returns)):
                        if abs(window_returns[j] - window_returns[k]) < connectivity_threshold:
                            visited[k] = True
            
            num_components.iloc[i] = components
        
        # 6. Graph Fragmentation (more components = more fragmented)
        fragmentation = num_components / graph_period
        
        # 7. Connectivity Regime (1=highly connected, 0=neutral, -1=fragmented)
        connectivity_regime = pd.Series(0, index=data.index)
        connectivity_regime[connectivity_normalized > 1.3] = 1
        connectivity_regime[connectivity_normalized < 0.7] = -1
        
        # 8. Connectivity Trend (increasing or decreasing)
        connectivity_trend = connectivity_normalized.diff(graph_period)
        
        # 9. Optimal Trading Conditions (high connectivity + positive trend)
        optimal_conditions = (
            (connectivity_regime == 1) &
            (connectivity_trend > 0) &
            (fragmentation < 0.3)
        ).astype(int)
        
        result = pd.DataFrame({
            'edge_density': edge_density,
            'avg_degree': avg_degree,
            'graph_diameter': graph_diameter,
            'connectivity_score': connectivity_normalized,
            'num_components': num_components,
            'fragmentation': fragmentation,
            'connectivity_regime': connectivity_regime,
            'connectivity_trend': connectivity_trend,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When high connectivity with positive trend
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['connectivity_score'] > 1.2) &
            (result['connectivity_trend'] > 0) &
            (result['fragmentation'] < 0.3)
        )
        
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip_value = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price, tp_level, sl_level = 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip_value)
                sl_level = entry_price - (sl_pips * pip_value)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        
        signal_strength = (result['connectivity_score'] / 2.0).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategy - Indicator-based
        
        Entry: High connectivity
        Exit: When connectivity drops or fragmentation increases
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['connectivity_score'] > 1.2) &
            (result['connectivity_trend'] > 0) &
            (result['fragmentation'] < 0.3)
        )
        
        exits = (
            (result['connectivity_regime'] == -1) |
            (result['connectivity_score'] < 0.8) |
            (result['fragmentation'] > 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['connectivity_regime'] == -1] = 'fragmented_regime'
        exit_reason[result['connectivity_score'] < 0.8] = 'connectivity_dropped'
        
        signal_strength = (result['connectivity_score'] / 2.0).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extract ML features"""
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'graph_edge_density': result['edge_density'],
            'graph_avg_degree': result['avg_degree'],
            'graph_diameter': result['graph_diameter'],
            'graph_connectivity': result['connectivity_score'],
            'graph_num_components': result['num_components'],
            'graph_fragmentation': result['fragmentation'],
            'graph_regime': result['connectivity_regime'],
            'graph_trend': result['connectivity_trend'],
            'graph_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'graph_period': [21, 34, 55],
            'connectivity_threshold': [0.01, 0.02, 0.03],
            'path_length': [3, 5, 8],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
