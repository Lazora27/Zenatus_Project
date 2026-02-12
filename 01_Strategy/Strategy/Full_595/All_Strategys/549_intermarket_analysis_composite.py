"""
549_intermarket_analysis_composite.py
======================================
Indicator: Intermarket Analysis Composite
Category: Master Indicators / Intermarket Relations
Complexity: Elite

Description:
-----------
Comprehensive intermarket analysis using multiple timeframes as proxies for
different markets. Analyzes leadership, divergences, and relative strength
across markets.

Key Features:
- Market leadership detection
- Intermarket divergence analysis
- Relative strength comparison
- Rotation signals

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_IntermarketAnalysisComposite:
    """
    Intermarket Analysis Composite
    
    Comprehensive intermarket relationship analysis.
    """
    
    def __init__(self):
        self.name = "Intermarket Analysis Composite"
        self.version = "1.0.0"
        self.category = "Master Indicators"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Intermarket Analysis metrics
        
        Parameters:
        - analysis_period: Period for analysis (default: 34)
        - divergence_threshold: Threshold for divergence (default: 0.02)
        - num_markets: Number of proxy markets (default: 4)
        """
        analysis_period = params.get('analysis_period', 34)
        divergence_threshold = params.get('divergence_threshold', 0.02)
        num_markets = params.get('num_markets', 4)
        
        returns = data['close'].pct_change()
        
        # Create proxy "markets" using different timeframes
        market_returns = []
        market_returns.append(returns)  # Market 1: Short-term
        market_returns.append(returns.rolling(window=5).mean())  # Market 2
        market_returns.append(returns.rolling(window=13).mean())  # Market 3
        market_returns.append(returns.rolling(window=21).mean())  # Market 4
        
        # 1. Relative Strength (each market vs average)
        avg_return = pd.concat(market_returns[:num_markets], axis=1).mean(axis=1)
        
        relative_strengths = []
        for i in range(num_markets):
            rs = market_returns[i] - avg_return
            relative_strengths.append(rs)
        
        # 2. Market Leadership (which market is strongest)
        rs_df = pd.concat(relative_strengths, axis=1)
        leader_index = rs_df.idxmax(axis=1)
        
        # 3. Leadership Strength (how much stronger is leader)
        leadership_strength = rs_df.max(axis=1) - rs_df.median(axis=1)
        
        # 4. Intermarket Divergence (markets moving in different directions)
        divergence_score = rs_df.std(axis=1)
        divergence_signal = (divergence_score > divergence_threshold).astype(int)
        
        # 5. Rotation Signal (leadership changing)
        rotation = (leader_index != leader_index.shift(1)).astype(int)
        
        # 6. Convergence (markets moving together)
        convergence = (divergence_score < divergence_threshold / 2).astype(int)
        
        # 7. Intermarket Momentum (aggregate momentum)
        intermarket_momentum = avg_return.rolling(window=analysis_period).sum()
        
        # 8. Breadth (how many markets are positive)
        positive_markets = pd.concat([mr > 0 for mr in market_returns[:num_markets]], axis=1).sum(axis=1)
        breadth = positive_markets / num_markets
        
        # 9. Optimal Conditions (strong breadth + convergence + positive momentum)
        optimal_conditions = (
            (breadth > 0.75) &
            (convergence == 1) &
            (intermarket_momentum > 0) &
            (divergence_signal == 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'avg_return': avg_return,
            'leadership_strength': leadership_strength,
            'divergence_score': divergence_score,
            'divergence_signal': divergence_signal,
            'rotation': rotation,
            'convergence': convergence,
            'intermarket_momentum': intermarket_momentum,
            'breadth': breadth,
            'optimal_conditions': optimal_conditions,
            'relative_strength_0': relative_strengths[0],
            'relative_strength_1': relative_strengths[1],
            'relative_strength_2': relative_strengths[2]
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['breadth'] > 0.75) &
            (result['intermarket_momentum'] > 0)
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
        signal_strength = result['breadth'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic Exit Strategy - Indicator-based"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['breadth'] > 0.75) &
            (result['intermarket_momentum'] > 0)
        )
        
        exits = (
            (result['divergence_signal'] == 1) |
            (result['breadth'] < 0.5) |
            (result['intermarket_momentum'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['divergence_signal'] == 1] = 'divergence'
        exit_reason[result['breadth'] < 0.5] = 'breadth_weak'
        
        signal_strength = result['breadth'].clip(0, 1)
        
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
            'inter_avg_return': result['avg_return'],
            'inter_leadership': result['leadership_strength'],
            'inter_divergence_score': result['divergence_score'],
            'inter_divergence': result['divergence_signal'],
            'inter_rotation': result['rotation'],
            'inter_convergence': result['convergence'],
            'inter_momentum': result['intermarket_momentum'],
            'inter_breadth': result['breadth'],
            'inter_optimal': result['optimal_conditions'],
            'inter_rs_0': result['relative_strength_0'],
            'inter_rs_1': result['relative_strength_1'],
            'inter_rs_2': result['relative_strength_2']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'analysis_period': [21, 34, 55],
            'divergence_threshold': [0.015, 0.020, 0.025],
            'num_markets': [3, 4, 5],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
