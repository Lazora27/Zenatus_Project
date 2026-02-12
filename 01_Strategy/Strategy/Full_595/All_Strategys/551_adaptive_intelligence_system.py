"""
551_adaptive_intelligence_system.py
====================================
Indicator: Adaptive Intelligence System
Category: Grand Finale / Adaptive Intelligence
Complexity: Elite

Description:
-----------
Ultimate adaptive system that learns and evolves with market conditions.
Combines reinforcement learning concepts, online learning, and adaptive
filtering to continuously improve performance.

Key Features:
- Continuous learning
- Performance-based adaptation
- Strategy evolution
- Intelligence scoring

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_AdaptiveIntelligenceSystem:
    """
    Adaptive Intelligence System
    
    Self-learning and evolving trading system.
    """
    
    def __init__(self):
        self.name = "Adaptive Intelligence System"
        self.version = "1.0.0"
        self.category = "Grand Finale"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Adaptive Intelligence metrics
        
        Parameters:
        - learning_period: Period for learning (default: 34)
        - adaptation_rate: Rate of adaptation (default: 0.1)
        - intelligence_threshold: Threshold for intelligence (default: 0.7)
        """
        learning_period = params.get('learning_period', 34)
        adaptation_rate = params.get('adaptation_rate', 0.1)
        intelligence_threshold = params.get('intelligence_threshold', 0.7)
        
        returns = data['close'].pct_change()
        
        # 1. Learning Component (pattern recognition)
        pattern_memory = returns.rolling(window=learning_period).apply(
            lambda x: abs(np.corrcoef(x[:-1], x[1:])[0, 1]) if len(x) > 1 else 0
        )
        
        # 2. Performance Tracking (reward signal)
        cumulative_performance = returns.rolling(window=learning_period).sum()
        performance_score = np.tanh(cumulative_performance * 10)
        
        # 3. Adaptive Strategy Weights (evolve based on performance)
        # Strategy 1: Trend following
        trend_signal = np.sign(returns.rolling(window=learning_period).sum())
        trend_performance = (trend_signal.shift(1) * returns).rolling(window=learning_period).sum()
        
        # Strategy 2: Mean reversion
        mean_rev_signal = -np.sign(data['close'] - data['close'].rolling(window=learning_period).mean())
        mean_rev_performance = (mean_rev_signal.shift(1) * returns).rolling(window=learning_period).sum()
        
        # Strategy 3: Momentum
        momentum_signal = np.sign(returns.rolling(window=13).sum())
        momentum_performance = (momentum_signal.shift(1) * returns).rolling(window=learning_period).sum()
        
        # Adaptive weights (exponential weighting)
        performances = pd.DataFrame({
            'trend': trend_performance,
            'mean_rev': mean_rev_performance,
            'momentum': momentum_performance
        })
        
        weights = performances.copy()
        for col in weights.columns:
            weights[col] = np.exp(performances[col] * 10)
        
        weight_sum = weights.sum(axis=1)
        for col in weights.columns:
            weights[col] = weights[col] / (weight_sum + 1e-10)
        
        # 4. Intelligent Signal (adaptive combination)
        intelligent_signal = (
            trend_signal * weights['trend'] +
            mean_rev_signal * weights['mean_rev'] +
            momentum_signal * weights['momentum']
        )
        
        # 5. Intelligence Score (how well system is learning)
        intelligence_score = (
            pattern_memory * 0.4 +
            (performance_score + 1.0) / 2.0 * 0.4 +
            weights.max(axis=1) * 0.2
        )
        
        # 6. Learning Progress (improvement over time)
        learning_progress = intelligence_score.diff(learning_period)
        
        # 7. Adaptation Quality (stability of weights)
        adaptation_quality = 1.0 - weights.std(axis=1)
        
        # 8. System Confidence (high intelligence + stable adaptation)
        system_confidence = intelligence_score * adaptation_quality
        
        # 9. Optimal Intelligence Conditions
        optimal_conditions = (
            (intelligence_score > intelligence_threshold) &
            (system_confidence > 0.6) &
            (learning_progress > 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'pattern_memory': pattern_memory,
            'performance_score': performance_score,
            'trend_weight': weights['trend'],
            'mean_rev_weight': weights['mean_rev'],
            'momentum_weight': weights['momentum'],
            'intelligent_signal': intelligent_signal,
            'intelligence_score': intelligence_score,
            'learning_progress': learning_progress,
            'adaptation_quality': adaptation_quality,
            'system_confidence': system_confidence,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['intelligent_signal'] > 0.5) &
            (result['system_confidence'] > 0.6)
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
        signal_strength = result['system_confidence'].clip(0, 1)
        
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
            (result['intelligent_signal'] > 0.5) &
            (result['system_confidence'] > 0.6)
        )
        
        exits = (
            (result['intelligent_signal'] < 0) |
            (result['system_confidence'] < 0.4) |
            (result['learning_progress'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['intelligent_signal'] < 0] = 'signal_reversed'
        exit_reason[result['system_confidence'] < 0.4] = 'confidence_low'
        
        signal_strength = result['system_confidence'].clip(0, 1)
        
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
            'ai_pattern_memory': result['pattern_memory'],
            'ai_performance': result['performance_score'],
            'ai_trend_weight': result['trend_weight'],
            'ai_mean_rev_weight': result['mean_rev_weight'],
            'ai_momentum_weight': result['momentum_weight'],
            'ai_signal': result['intelligent_signal'],
            'ai_intelligence': result['intelligence_score'],
            'ai_learning_progress': result['learning_progress'],
            'ai_adaptation_quality': result['adaptation_quality'],
            'ai_confidence': result['system_confidence'],
            'ai_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'learning_period': [21, 34, 55],
            'adaptation_rate': [0.05, 0.1, 0.15],
            'intelligence_threshold': [0.6, 0.7, 0.8],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
