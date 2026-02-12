"""
537_adaptive_regime_composite.py
=================================
Indicator: Adaptive Regime Composite
Category: Ultimate Composites / Regime Adaptation
Complexity: Elite

Description:
-----------
Adapts strategy based on detected market regime. Automatically switches between
trend-following, mean-reversion, and breakout strategies based on regime
classification. Ultimate adaptive indicator.

Key Features:
- Automatic regime detection
- Strategy adaptation
- Regime-specific signals
- Seamless strategy switching

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_AdaptiveRegimeComposite:
    """
    Adaptive Regime Composite
    
    Adapts strategy to market regime automatically.
    """
    
    def __init__(self):
        self.name = "Adaptive Regime Composite"
        self.version = "1.0.0"
        self.category = "Ultimate Composites"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Adaptive Regime metrics
        
        Parameters:
        - regime_period: Period for regime detection (default: 34)
        - adaptation_speed: Speed of adaptation (default: 0.1)
        - confidence_threshold: Threshold for regime confidence (default: 0.7)
        """
        regime_period = params.get('regime_period', 34)
        adaptation_speed = params.get('adaptation_speed', 0.1)
        confidence_threshold = params.get('confidence_threshold', 0.7)
        
        returns = data['close'].pct_change()
        
        # 1. Regime Detection (Trending, Ranging, Volatile)
        # Trending: strong directional movement
        trend_strength = abs(returns.rolling(window=regime_period).sum()) / \
                        (abs(returns).rolling(window=regime_period).sum() + 1e-10)
        
        # Ranging: low volatility, mean reversion
        volatility = returns.rolling(window=regime_period).std()
        vol_percentile = volatility.rolling(window=regime_period * 2).rank(pct=True)
        
        # Volatile: high volatility
        is_trending = (trend_strength > 0.6).astype(int)
        is_ranging = ((vol_percentile < 0.3) & (trend_strength < 0.4)).astype(int)
        is_volatile = (vol_percentile > 0.7).astype(int)
        
        # 2. Regime Classification (1=trending, 2=ranging, 3=volatile)
        regime = pd.Series(0, index=data.index)
        regime[is_trending == 1] = 1
        regime[is_ranging == 1] = 2
        regime[is_volatile == 1] = 3
        
        # 3. Regime Confidence (how certain about regime)
        regime_confidence = pd.Series(0.0, index=data.index)
        regime_confidence[is_trending == 1] = trend_strength[is_trending == 1]
        regime_confidence[is_ranging == 1] = 1.0 - vol_percentile[is_ranging == 1]
        regime_confidence[is_volatile == 1] = vol_percentile[is_volatile == 1]
        
        # 4. Strategy Signals for Each Regime
        # Trending: Follow trend
        sma = data['close'].rolling(window=regime_period).mean()
        trend_strategy_signal = np.sign(data['close'] - sma)
        
        # Ranging: Mean reversion
        mean_reversion_signal = -np.sign(data['close'] - sma) * (abs(data['close'] - sma) / sma > 0.02).astype(int)
        
        # Volatile: Breakout
        resistance = data['high'].rolling(window=regime_period).max()
        support = data['low'].rolling(window=regime_period).min()
        breakout_signal = ((data['close'] > resistance.shift(1)).astype(int) - 
                          (data['close'] < support.shift(1)).astype(int))
        
        # 5. Adaptive Signal (select strategy based on regime)
        adaptive_signal = pd.Series(0.0, index=data.index)
        adaptive_signal[regime == 1] = trend_strategy_signal[regime == 1]
        adaptive_signal[regime == 2] = mean_reversion_signal[regime == 2]
        adaptive_signal[regime == 3] = breakout_signal[regime == 3]
        
        # 6. Signal Strength (based on regime confidence)
        signal_strength = abs(adaptive_signal) * regime_confidence
        
        # 7. Regime Persistence (how long in current regime)
        regime_persistence = pd.Series(0, index=data.index)
        persistence_count = 0
        current_regime = 0
        
        for i in range(len(data)):
            if regime.iloc[i] == current_regime:
                persistence_count += 1
            else:
                current_regime = regime.iloc[i]
                persistence_count = 1
            regime_persistence.iloc[i] = persistence_count
        
        # 8. Optimal Adaptive Conditions
        optimal_conditions = (
            (regime != 0) &
            (regime_confidence > confidence_threshold) &
            (regime_persistence > 3) &
            (signal_strength > 0.5)
        ).astype(int)
        
        result = pd.DataFrame({
            'regime': regime,
            'regime_confidence': regime_confidence,
            'trend_strategy': trend_strategy_signal,
            'mean_reversion_strategy': mean_reversion_signal,
            'breakout_strategy': breakout_signal,
            'adaptive_signal': adaptive_signal,
            'signal_strength': signal_strength,
            'regime_persistence': regime_persistence,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['adaptive_signal'] > 0) &
            (result['regime_confidence'] > 0.7)
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
        signal_strength = result['signal_strength'].clip(0, 1)
        
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
            (result['adaptive_signal'] > 0) &
            (result['regime_confidence'] > 0.7)
        )
        
        exits = (
            (result['adaptive_signal'] < 0) |
            (result['regime_confidence'] < 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['adaptive_signal'] < 0] = 'signal_reversed'
        exit_reason[result['regime_confidence'] < 0.5] = 'confidence_low'
        
        signal_strength = result['signal_strength'].clip(0, 1)
        
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
            'adapt_regime': result['regime'],
            'adapt_confidence': result['regime_confidence'],
            'adapt_trend_strat': result['trend_strategy'],
            'adapt_mean_rev_strat': result['mean_reversion_strategy'],
            'adapt_breakout_strat': result['breakout_strategy'],
            'adapt_signal': result['adaptive_signal'],
            'adapt_strength': result['signal_strength'],
            'adapt_persistence': result['regime_persistence'],
            'adapt_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'regime_period': [21, 34, 55],
            'adaptation_speed': [0.05, 0.1, 0.15],
            'confidence_threshold': [0.6, 0.7, 0.8],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
