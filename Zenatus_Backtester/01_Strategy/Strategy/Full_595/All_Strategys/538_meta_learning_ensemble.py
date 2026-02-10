"""
538_meta_learning_ensemble.py
==============================
Indicator: Meta-Learning Ensemble
Category: Ultimate Composites / Meta-Learning
Complexity: Elite

Description:
-----------
Meta-learning ensemble that learns which indicators work best in which conditions.
Combines multiple base indicators and learns optimal weighting dynamically.
Ultimate adaptive ensemble.

Key Features:
- Multi-indicator ensemble
- Dynamic weight learning
- Performance-based adaptation
- Meta-level optimization

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MetaLearningEnsemble:
    """
    Meta-Learning Ensemble
    
    Learns optimal indicator combination dynamically.
    """
    
    def __init__(self):
        self.name = "Meta-Learning Ensemble"
        self.version = "1.0.0"
        self.category = "Ultimate Composites"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Meta-Learning Ensemble metrics
        
        Parameters:
        - ensemble_period: Period for ensemble learning (default: 34)
        - learning_rate: Learning rate for weight updates (default: 0.1)
        - num_base_indicators: Number of base indicators (default: 5)
        """
        ensemble_period = params.get('ensemble_period', 34)
        learning_rate = params.get('learning_rate', 0.1)
        num_base_indicators = params.get('num_base_indicators', 5)
        
        returns = data['close'].pct_change()
        
        # Base Indicators
        base_indicators = []
        
        # 1. RSI
        rsi = talib.RSI(data['close'].values, timeperiod=14)
        rsi_signal = (rsi - 50) / 50
        base_indicators.append(pd.Series(rsi_signal, index=data.index))
        
        # 2. MACD
        macd, signal, hist = talib.MACD(data['close'].values)
        macd_signal = np.sign(hist)
        base_indicators.append(pd.Series(macd_signal, index=data.index))
        
        # 3. Bollinger Bands
        upper, middle, lower = talib.BBANDS(data['close'].values)
        bb_signal = (data['close'].values - middle) / (upper - lower + 1e-10)
        base_indicators.append(pd.Series(bb_signal, index=data.index))
        
        # 4. ADX
        adx = talib.ADX(data['high'].values, data['low'].values, data['close'].values)
        adx_signal = (adx - 25) / 75
        base_indicators.append(pd.Series(adx_signal, index=data.index))
        
        # 5. Stochastic
        slowk, slowd = talib.STOCH(data['high'].values, data['low'].values, data['close'].values)
        stoch_signal = (slowk - 50) / 50
        base_indicators.append(pd.Series(stoch_signal, index=data.index))
        
        # Meta-Learning: Track performance of each indicator
        indicator_performances = pd.DataFrame(index=data.index)
        
        for i, indicator in enumerate(base_indicators[:num_base_indicators]):
            # Performance = indicator signal * future return
            perf = (indicator.shift(1) * returns).rolling(window=ensemble_period).sum()
            indicator_performances[f'ind_{i}'] = perf
        
        # Dynamic Weights (exponential weighting based on performance)
        indicator_weights = indicator_performances.copy()
        for col in indicator_weights.columns:
            indicator_weights[col] = np.exp(indicator_performances[col] * 10)
        
        weight_sum = indicator_weights.sum(axis=1)
        for col in indicator_weights.columns:
            indicator_weights[col] = indicator_weights[col] / (weight_sum + 1e-10)
        
        # Ensemble Prediction (weighted combination)
        ensemble_signal = pd.Series(0.0, index=data.index)
        
        for i in range(num_base_indicators):
            if i < len(base_indicators):
                ensemble_signal += base_indicators[i] * indicator_weights[f'ind_{i}']
        
        # Ensemble Confidence (concentration of weights)
        max_weight = indicator_weights.max(axis=1)
        ensemble_confidence = 1.0 - (max_weight - 1.0/num_base_indicators) / (1.0 - 1.0/num_base_indicators)
        
        # Meta-Learning Performance
        meta_performance = (ensemble_signal.shift(1) * returns).rolling(window=ensemble_period).sum()
        
        # Optimal Ensemble Conditions
        optimal_conditions = (
            (abs(ensemble_signal) > 0.5) &
            (meta_performance > 0) &
            (ensemble_confidence > 0.6)
        ).astype(int)
        
        result = pd.DataFrame({
            'ensemble_signal': ensemble_signal,
            'ensemble_confidence': ensemble_confidence,
            'meta_performance': meta_performance,
            'optimal_conditions': optimal_conditions,
            'weight_0': indicator_weights['ind_0'],
            'weight_1': indicator_weights['ind_1'],
            'weight_2': indicator_weights['ind_2'],
            'weight_3': indicator_weights['ind_3'],
            'weight_4': indicator_weights['ind_4']
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['ensemble_signal'] > 0.5) &
            (result['meta_performance'] > 0)
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
        signal_strength = abs(result['ensemble_signal']).clip(0, 1)
        
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
            (result['ensemble_signal'] > 0.5) &
            (result['meta_performance'] > 0)
        )
        
        exits = (
            (result['ensemble_signal'] < 0) |
            (result['meta_performance'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['ensemble_signal'] < 0] = 'ensemble_reversed'
        exit_reason[result['meta_performance'] < 0] = 'performance_negative'
        
        signal_strength = abs(result['ensemble_signal']).clip(0, 1)
        
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
            'meta_ensemble_signal': result['ensemble_signal'],
            'meta_confidence': result['ensemble_confidence'],
            'meta_performance': result['meta_performance'],
            'meta_optimal': result['optimal_conditions'],
            'meta_weight_0': result['weight_0'],
            'meta_weight_1': result['weight_1'],
            'meta_weight_2': result['weight_2'],
            'meta_weight_3': result['weight_3'],
            'meta_weight_4': result['weight_4']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'ensemble_period': [21, 34, 55],
            'learning_rate': [0.05, 0.1, 0.15],
            'num_base_indicators': [3, 5, 7],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
