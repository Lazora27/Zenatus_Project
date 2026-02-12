"""
534_long_short_equity_indicator.py
===================================
Indicator: Long Short Equity Indicator
Category: Exotic Strategies / Equity Strategies
Complexity: Elite

Description:
-----------
Implements long/short equity strategy by identifying relative winners and losers.
Goes long strong performers, short weak performers. Uses relative strength,
momentum, and quality factors for selection.

Key Features:
- Relative strength ranking
- Long/short signal generation
- Portfolio balance optimization
- Factor-based selection

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_LongShortEquityIndicator:
    """
    Long Short Equity Indicator
    
    Generates long/short equity signals.
    """
    
    def __init__(self):
        self.name = "Long Short Equity Indicator"
        self.version = "1.0.0"
        self.category = "Exotic Strategies"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Long Short Equity metrics
        
        Parameters:
        - ranking_period: Period for ranking (default: 21)
        - momentum_period: Period for momentum (default: 13)
        - quality_period: Period for quality assessment (default: 34)
        """
        ranking_period = params.get('ranking_period', 21)
        momentum_period = params.get('momentum_period', 13)
        quality_period = params.get('quality_period', 34)
        
        returns = data['close'].pct_change()
        
        # === FACTOR 1: Momentum Score ===
        momentum_score = returns.rolling(window=momentum_period).sum()
        momentum_rank = momentum_score.rolling(window=ranking_period).rank(pct=True)
        
        # === FACTOR 2: Volatility Quality (low volatility = high quality) ===
        volatility = returns.rolling(window=quality_period).std()
        volatility_rank = volatility.rolling(window=ranking_period).rank(pct=True)
        quality_score = 1.0 - volatility_rank  # Invert: low vol = high quality
        
        # === FACTOR 3: Trend Strength ===
        sma_fast = data['close'].rolling(window=momentum_period).mean()
        sma_slow = data['close'].rolling(window=ranking_period).mean()
        
        trend_strength = (sma_fast - sma_slow) / (sma_slow + 1e-10)
        trend_rank = trend_strength.rolling(window=ranking_period).rank(pct=True)
        
        # === FACTOR 4: Volume Quality ===
        volume_trend = data['volume'].rolling(window=momentum_period).mean() / \
                       data['volume'].rolling(window=quality_period).mean()
        volume_rank = volume_trend.rolling(window=ranking_period).rank(pct=True)
        
        # === COMPOSITE SCORE ===
        composite_score = (
            momentum_rank * 0.35 +
            quality_score * 0.25 +
            trend_rank * 0.25 +
            volume_rank * 0.15
        )
        
        # 5. Long Candidate (top performers)
        long_candidate = (composite_score > 0.7).astype(int)
        
        # 6. Short Candidate (bottom performers)
        short_candidate = (composite_score < 0.3).astype(int)
        
        # 7. Relative Strength (vs average)
        relative_strength = composite_score - 0.5
        
        # 8. Long Signal Strength
        long_strength = (composite_score - 0.7) / 0.3
        long_strength = long_strength.clip(0, 1)
        
        # 9. Short Signal Strength
        short_strength = (0.3 - composite_score) / 0.3
        short_strength = short_strength.clip(0, 1)
        
        # 10. Optimal Long Conditions (strong + quality + momentum)
        optimal_long = (
            (long_candidate == 1) &
            (momentum_rank > 0.7) &
            (quality_score > 0.6) &
            (trend_rank > 0.6)
        ).astype(int)
        
        result = pd.DataFrame({
            'momentum_rank': momentum_rank,
            'quality_score': quality_score,
            'trend_rank': trend_rank,
            'volume_rank': volume_rank,
            'composite_score': composite_score,
            'long_candidate': long_candidate,
            'short_candidate': short_candidate,
            'relative_strength': relative_strength,
            'long_strength': long_strength,
            'short_strength': short_strength,
            'optimal_long': optimal_long
        }, index=data.index)
        
        return result.fillna(0.5)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal long conditions
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_long'] == 1) &
            (result['composite_score'] > 0.75) &
            (result['relative_strength'] > 0.25)
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
        
        signal_strength = result['long_strength']
        
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
        
        Entry: Optimal long
        Exit: When relative strength weakens
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_long'] == 1) &
            (result['composite_score'] > 0.75) &
            (result['relative_strength'] > 0.25)
        )
        
        exits = (
            (result['composite_score'] < 0.5) |
            (result['long_candidate'] == 0) |
            (result['relative_strength'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['composite_score'] < 0.5] = 'score_dropped'
        exit_reason[result['long_candidate'] == 0] = 'no_longer_long'
        exit_reason[result['relative_strength'] < 0] = 'relative_weakness'
        
        signal_strength = result['long_strength']
        
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
            'ls_momentum_rank': result['momentum_rank'],
            'ls_quality_score': result['quality_score'],
            'ls_trend_rank': result['trend_rank'],
            'ls_volume_rank': result['volume_rank'],
            'ls_composite_score': result['composite_score'],
            'ls_long_candidate': result['long_candidate'],
            'ls_short_candidate': result['short_candidate'],
            'ls_relative_strength': result['relative_strength'],
            'ls_long_strength': result['long_strength'],
            'ls_short_strength': result['short_strength'],
            'ls_optimal_long': result['optimal_long']
        }, index=data.index)
        
        return features.fillna(0.5)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'ranking_period': [13, 21, 34],
            'momentum_period': [8, 13, 21],
            'quality_period': [21, 34, 55],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
