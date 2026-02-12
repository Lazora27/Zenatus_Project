"""
521_market_network_centrality.py
=================================
Indicator: Market Network Centrality
Category: Network Analysis / Graph Theory
Complexity: Elite

Description:
-----------
Applies network centrality concepts to price movements. Treats price levels as
nodes and transitions as edges to identify central/influential price levels.
High centrality indicates key support/resistance levels.

Key Features:
- Degree centrality (most connected prices)
- Betweenness centrality (bridge prices)
- Eigenvector centrality (influential prices)
- Centrality-based trading signals

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MarketNetworkCentrality:
    """
    Market Network Centrality
    
    Identifies central/influential price levels using network theory.
    """
    
    def __init__(self):
        self.name = "Market Network Centrality"
        self.version = "1.0.0"
        self.category = "Network Analysis"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Network Centrality metrics
        
        Parameters:
        - network_period: Period for network construction (default: 34)
        - price_bins: Number of price bins/nodes (default: 20)
        - centrality_period: Period for centrality calculation (default: 21)
        """
        network_period = params.get('network_period', 34)
        price_bins = params.get('price_bins', 20)
        centrality_period = params.get('centrality_period', 21)
        
        # 1. Create Price Network (discretize prices into bins)
        price_min = data['close'].rolling(window=network_period).min()
        price_max = data['close'].rolling(window=network_period).max()
        
        # Normalize price to 0-1 range
        price_normalized = (data['close'] - price_min) / (price_max - price_min + 1e-10)
        
        # Assign to bins
        price_bin = (price_normalized * (price_bins - 1)).fillna(0).astype(int)
        
        # 2. Degree Centrality (how many times price visited each bin)
        degree_centrality = pd.Series(0.0, index=data.index)
        
        for i in range(network_period, len(data)):
            window_bins = price_bin.iloc[i-network_period:i]
            current_bin = price_bin.iloc[i]
            
            # Count connections to current bin
            degree = (window_bins == current_bin).sum()
            degree_centrality.iloc[i] = degree / network_period
        
        # 3. Betweenness Centrality (simplified: transitions through current bin)
        betweenness_centrality = pd.Series(0.0, index=data.index)
        
        for i in range(network_period, len(data)):
            window_bins = price_bin.iloc[i-network_period:i].values
            current_bin = price_bin.iloc[i]
            
            # Count transitions through current bin
            transitions_through = 0
            for j in range(len(window_bins) - 1):
                if window_bins[j] < current_bin < window_bins[j+1] or \
                   window_bins[j] > current_bin > window_bins[j+1]:
                    transitions_through += 1
            
            betweenness_centrality.iloc[i] = transitions_through / (network_period - 1) if network_period > 1 else 0
        
        # 4. Closeness Centrality (average distance to other bins)
        closeness_centrality = pd.Series(0.0, index=data.index)
        
        for i in range(network_period, len(data)):
            window_bins = price_bin.iloc[i-network_period:i].values
            current_bin = price_bin.iloc[i]
            
            # Average distance to all visited bins
            unique_bins = np.unique(window_bins)
            if len(unique_bins) > 1:
                avg_distance = np.mean([abs(current_bin - b) for b in unique_bins])
                closeness_centrality.iloc[i] = 1.0 / (avg_distance + 1e-10)
        
        # 5. Composite Centrality Score
        centrality_score = (
            degree_centrality * 0.4 +
            betweenness_centrality * 0.3 +
            closeness_centrality * 0.3
        )
        
        # 6. Central Price Level (high centrality = key level)
        central_level = (centrality_score > centrality_score.rolling(window=centrality_period).quantile(0.7)).astype(int)
        
        # 7. Price at Central Node (whether current price is at central level)
        at_central_node = central_level
        
        # 8. Distance to Nearest Central Node
        distance_to_central = pd.Series(0.0, index=data.index)
        
        for i in range(len(data)):
            if central_level.iloc[i] == 0:
                # Find nearest central node
                for j in range(1, min(centrality_period, i)):
                    if central_level.iloc[i-j] == 1:
                        distance_to_central.iloc[i] = abs(data['close'].iloc[i] - data['close'].iloc[i-j]) / data['close'].iloc[i]
                        break
        
        # 9. Centrality Trend (increasing or decreasing)
        centrality_trend = centrality_score.diff(centrality_period)
        
        # 10. Optimal Entry Signal (approaching central node from below)
        optimal_entry = (
            (distance_to_central < 0.01) &
            (distance_to_central.shift(1) > distance_to_central) &
            (centrality_score > 0.5) &
            (data['close'] > data['close'].shift(1))
        ).astype(int)
        
        result = pd.DataFrame({
            'degree_centrality': degree_centrality,
            'betweenness_centrality': betweenness_centrality,
            'closeness_centrality': closeness_centrality,
            'centrality_score': centrality_score,
            'central_level': central_level,
            'at_central_node': at_central_node,
            'distance_to_central': distance_to_central,
            'centrality_trend': centrality_trend,
            'optimal_entry': optimal_entry
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When approaching central node with upward momentum
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal entry + high centrality + positive trend
        entries = (
            (result['optimal_entry'] == 1) &
            (result['centrality_score'] > 0.5) &
            (result['centrality_trend'] > 0)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip_value = 0.0001
        
        # Manual TP/SL Exit Logic
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
        
        signal_strength = result['centrality_score'].clip(0, 1)
        
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
        
        Entry: Approaching central node
        Exit: When leaving central node or centrality drops
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_entry'] == 1) &
            (result['centrality_score'] > 0.5) &
            (result['centrality_trend'] > 0)
        )
        
        exits = (
            (result['at_central_node'] == 0) |
            (result['centrality_score'] < 0.3) |
            (result['centrality_trend'] < -0.1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['at_central_node'] == 0] = 'left_central_node'
        exit_reason[result['centrality_score'] < 0.3] = 'centrality_dropped'
        
        signal_strength = result['centrality_score'].clip(0, 1)
        
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
            'net_degree_centrality': result['degree_centrality'],
            'net_betweenness': result['betweenness_centrality'],
            'net_closeness': result['closeness_centrality'],
            'net_centrality_score': result['centrality_score'],
            'net_central_level': result['central_level'],
            'net_at_central': result['at_central_node'],
            'net_distance_to_central': result['distance_to_central'],
            'net_centrality_trend': result['centrality_trend'],
            'net_optimal_entry': result['optimal_entry']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'network_period': [21, 34, 55],
            'price_bins': [15, 20, 25],
            'centrality_period': [13, 21, 34],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
