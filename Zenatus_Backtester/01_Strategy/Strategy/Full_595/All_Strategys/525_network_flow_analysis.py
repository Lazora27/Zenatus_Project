"""
525_network_flow_analysis.py
=============================
Indicator: Network Flow Analysis
Category: Network Analysis / Flow Theory
Complexity: Elite

Description:
-----------
Analyzes flow in price movement networks. Measures how price "flows" through
different states/levels. High flow indicates strong directional movement,
low flow indicates congestion. Uses max-flow concepts from graph theory.

Key Features:
- Flow capacity measurement
- Bottleneck detection
- Flow direction analysis
- Congestion identification

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_NetworkFlowAnalysis:
    """
    Network Flow Analysis
    
    Analyzes flow in price movement networks.
    """
    
    def __init__(self):
        self.name = "Network Flow Analysis"
        self.version = "1.0.0"
        self.category = "Network Analysis"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Network Flow metrics
        
        Parameters:
        - flow_period: Period for flow analysis (default: 21)
        - capacity_period: Period for capacity calculation (default: 13)
        - congestion_threshold: Threshold for congestion (default: 0.5)
        """
        flow_period = params.get('flow_period', 21)
        capacity_period = params.get('capacity_period', 13)
        congestion_threshold = params.get('congestion_threshold', 0.5)
        
        returns = data['close'].pct_change()
        
        # 1. Flow Rate (speed of price movement)
        flow_rate = abs(returns).rolling(window=flow_period).mean()
        flow_rate_normalized = flow_rate / flow_rate.rolling(window=50).mean()
        
        # 2. Flow Capacity (maximum sustainable flow)
        # Based on volume and volatility
        volatility = returns.rolling(window=capacity_period).std()
        volume_normalized = data['volume'] / data['volume'].rolling(window=capacity_period).mean()
        
        flow_capacity = volume_normalized / (volatility + 1e-10)
        flow_capacity_normalized = flow_capacity / flow_capacity.rolling(window=50).mean()
        
        # 3. Flow Utilization (current flow / capacity)
        flow_utilization = flow_rate_normalized / (flow_capacity_normalized + 1e-10)
        
        # 4. Flow Direction (net directional flow)
        flow_direction = returns.rolling(window=flow_period).sum()
        flow_direction_strength = abs(flow_direction) / (abs(returns).rolling(window=flow_period).sum() + 1e-10)
        
        # 5. Bottleneck Detection (low capacity + high utilization)
        bottleneck = (
            (flow_capacity_normalized < 0.7) &
            (flow_utilization > 1.3)
        ).astype(int)
        
        # 6. Congestion Score (flow rate below capacity)
        congestion_score = pd.Series(0.0, index=data.index)
        congestion_score[flow_utilization < congestion_threshold] = 1.0 - flow_utilization[flow_utilization < congestion_threshold]
        
        # 7. Free Flow (high capacity + low utilization)
        free_flow = (
            (flow_capacity_normalized > 1.2) &
            (flow_utilization < 0.8) &
            (flow_direction_strength > 0.6)
        ).astype(int)
        
        # 8. Flow Regime (1=free flow, 0=normal, -1=congested)
        flow_regime = pd.Series(0, index=data.index)
        flow_regime[free_flow == 1] = 1
        flow_regime[congestion_score > 0.5] = -1
        
        # 9. Flow Momentum (acceleration of flow)
        flow_momentum = flow_rate_normalized.diff(capacity_period)
        
        # 10. Optimal Flow Conditions (free flow + strong direction + positive momentum)
        optimal_flow = (
            (free_flow == 1) &
            (flow_direction_strength > 0.6) &
            (flow_momentum > 0) &
            (bottleneck == 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'flow_rate': flow_rate_normalized,
            'flow_capacity': flow_capacity_normalized,
            'flow_utilization': flow_utilization,
            'flow_direction': flow_direction,
            'flow_direction_strength': flow_direction_strength,
            'bottleneck': bottleneck,
            'congestion_score': congestion_score,
            'free_flow': free_flow,
            'flow_regime': flow_regime,
            'flow_momentum': flow_momentum,
            'optimal_flow': optimal_flow
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal flow conditions (free flow + direction)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_flow'] == 1) &
            (result['flow_direction_strength'] > 0.6) &
            (result['flow_momentum'] > 0) &
            (result['congestion_score'] < 0.3)
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
        
        signal_strength = result['flow_direction_strength'].clip(0, 1)
        
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
        
        Entry: Optimal flow
        Exit: When congestion or bottleneck appears
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_flow'] == 1) &
            (result['flow_direction_strength'] > 0.6) &
            (result['flow_momentum'] > 0) &
            (result['congestion_score'] < 0.3)
        )
        
        exits = (
            (result['flow_regime'] == -1) |
            (result['bottleneck'] == 1) |
            (result['congestion_score'] > 0.5) |
            (result['flow_momentum'] < -0.2)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['flow_regime'] == -1] = 'congested_regime'
        exit_reason[result['bottleneck'] == 1] = 'bottleneck_detected'
        exit_reason[result['congestion_score'] > 0.5] = 'high_congestion'
        
        signal_strength = result['flow_direction_strength'].clip(0, 1)
        
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
            'flow_rate': result['flow_rate'],
            'flow_capacity': result['flow_capacity'],
            'flow_utilization': result['flow_utilization'],
            'flow_direction': result['flow_direction'],
            'flow_direction_strength': result['flow_direction_strength'],
            'flow_bottleneck': result['bottleneck'],
            'flow_congestion': result['congestion_score'],
            'flow_free_flow': result['free_flow'],
            'flow_regime': result['flow_regime'],
            'flow_momentum': result['flow_momentum'],
            'flow_optimal': result['optimal_flow']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'flow_period': [13, 21, 34],
            'capacity_period': [8, 13, 21],
            'congestion_threshold': [0.4, 0.5, 0.6],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
