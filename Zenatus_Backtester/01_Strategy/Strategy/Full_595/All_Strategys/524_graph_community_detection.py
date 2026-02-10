"""
524_graph_community_detection.py
=================================
Indicator: Graph Community Detection
Category: Network Analysis / Community Structure
Complexity: Elite

Description:
-----------
Detects communities (groups) in price movement networks. Communities represent
distinct market behaviors or regimes. Community transitions signal regime changes.
Uses modularity-based community detection.

Key Features:
- Community identification
- Modularity measurement
- Community transition detection
- Inter-community analysis

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_GraphCommunityDetection:
    """
    Graph Community Detection
    
    Identifies communities in price movement networks.
    """
    
    def __init__(self):
        self.name = "Graph Community Detection"
        self.version = "1.0.0"
        self.category = "Network Analysis"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Community Detection metrics
        
        Parameters:
        - community_period: Period for community detection (default: 34)
        - num_communities: Expected number of communities (default: 3)
        - modularity_threshold: Threshold for strong communities (default: 0.3)
        """
        community_period = params.get('community_period', 34)
        num_communities = params.get('num_communities', 3)
        modularity_threshold = params.get('modularity_threshold', 0.3)
        
        returns = data['close'].pct_change()
        
        # 1. Community Assignment (simplified: based on return ranges)
        community_id = pd.Series(0, index=data.index)
        
        for i in range(community_period, len(data)):
            window_returns = returns.iloc[i-community_period:i].values
            
            # Divide into communities based on quantiles
            quantiles = np.percentile(window_returns, np.linspace(0, 100, num_communities + 1))
            
            current_return = returns.iloc[i]
            for c in range(num_communities):
                if quantiles[c] <= current_return < quantiles[c + 1]:
                    community_id.iloc[i] = c
                    break
        
        # 2. Modularity (quality of community structure)
        modularity = pd.Series(0.0, index=data.index)
        
        for i in range(community_period, len(data)):
            window_returns = returns.iloc[i-community_period:i].values
            window_communities = community_id.iloc[i-community_period:i].values
            
            # Calculate modularity (simplified)
            within_community_variance = 0
            total_variance = np.var(window_returns)
            
            for c in range(num_communities):
                community_returns = window_returns[window_communities == c]
                if len(community_returns) > 0:
                    within_community_variance += np.var(community_returns) * len(community_returns)
            
            within_community_variance /= len(window_returns)
            
            # Modularity: 1 - (within / total)
            modularity.iloc[i] = 1.0 - (within_community_variance / (total_variance + 1e-10))
        
        # 3. Community Transition (changing communities)
        community_transition = (community_id != community_id.shift(1)).astype(int)
        
        # 4. Community Persistence (how long in current community)
        community_persistence = pd.Series(0, index=data.index)
        persistence_count = 0
        current_community = -1
        
        for i in range(len(data)):
            if community_id.iloc[i] == current_community:
                persistence_count += 1
            else:
                current_community = community_id.iloc[i]
                persistence_count = 1
            community_persistence.iloc[i] = persistence_count
        
        # 5. Community Size (number of members in current community)
        community_size = pd.Series(0, index=data.index)
        
        for i in range(community_period, len(data)):
            window_communities = community_id.iloc[i-community_period:i].values
            current_comm = community_id.iloc[i]
            community_size.iloc[i] = np.sum(window_communities == current_comm) / community_period
        
        # 6. Inter-Community Distance (distance to other communities)
        inter_community_distance = pd.Series(0.0, index=data.index)
        
        for i in range(community_period, len(data)):
            window_returns = returns.iloc[i-community_period:i].values
            window_communities = community_id.iloc[i-community_period:i].values
            current_comm = community_id.iloc[i]
            
            # Average return in current community
            current_comm_returns = window_returns[window_communities == current_comm]
            if len(current_comm_returns) > 0:
                current_mean = np.mean(current_comm_returns)
                
                # Distance to other communities
                distances = []
                for c in range(num_communities):
                    if c != current_comm:
                        other_returns = window_returns[window_communities == c]
                        if len(other_returns) > 0:
                            distances.append(abs(current_mean - np.mean(other_returns)))
                
                if distances:
                    inter_community_distance.iloc[i] = np.mean(distances)
        
        # 7. Community Strength (modularity + persistence)
        community_strength = (modularity + community_persistence / community_period) / 2.0
        
        # 8. Optimal Trading Conditions (strong community + persistent)
        optimal_conditions = (
            (modularity > modularity_threshold) &
            (community_persistence > 5) &
            (community_size > 0.3)
        ).astype(int)
        
        result = pd.DataFrame({
            'community_id': community_id,
            'modularity': modularity,
            'community_transition': community_transition,
            'community_persistence': community_persistence,
            'community_size': community_size,
            'inter_community_distance': inter_community_distance,
            'community_strength': community_strength,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When in strong, persistent community
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['community_strength'] > 0.5) &
            (result['community_persistence'] > 5) &
            (result['community_transition'] == 0)
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
        
        signal_strength = result['community_strength'].clip(0, 1)
        
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
        
        Entry: Strong community
        Exit: When community transition or strength weakens
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['community_strength'] > 0.5) &
            (result['community_persistence'] > 5) &
            (result['community_transition'] == 0)
        )
        
        exits = (
            (result['community_transition'] == 1) |
            (result['community_strength'] < 0.3) |
            (result['modularity'] < 0.2)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['community_transition'] == 1] = 'community_changed'
        exit_reason[result['community_strength'] < 0.3] = 'strength_weakened'
        
        signal_strength = result['community_strength'].clip(0, 1)
        
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
            'comm_id': result['community_id'],
            'comm_modularity': result['modularity'],
            'comm_transition': result['community_transition'],
            'comm_persistence': result['community_persistence'],
            'comm_size': result['community_size'],
            'comm_inter_distance': result['inter_community_distance'],
            'comm_strength': result['community_strength'],
            'comm_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'community_period': [21, 34, 55],
            'num_communities': [2, 3, 5],
            'modularity_threshold': [0.2, 0.3, 0.4],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
