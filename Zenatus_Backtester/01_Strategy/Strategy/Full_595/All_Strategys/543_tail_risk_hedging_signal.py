"""
543_tail_risk_hedging_signal.py
================================
Indicator: Tail Risk Hedging Signal
Category: Risk Management / Tail Risk
Complexity: Elite

Description:
-----------
Detects tail risk conditions and generates hedging signals. Identifies when
extreme events (black swans) become more likely. Uses extreme value theory
and tail distribution analysis.

Key Features:
- Tail risk measurement
- Extreme event probability
- Hedging signal generation
- Tail distribution analysis

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_TailRiskHedgingSignal:
    """
    Tail Risk Hedging Signal
    
    Detects and hedges tail risk.
    """
    
    def __init__(self):
        self.name = "Tail Risk Hedging Signal"
        self.version = "1.0.0"
        self.category = "Risk Management"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Tail Risk metrics
        
        Parameters:
        - tail_period: Period for tail analysis (default: 55)
        - tail_threshold: Threshold for tail events (default: 2.5)
        - hedge_threshold: Threshold for hedging (default: 0.3)
        """
        tail_period = params.get('tail_period', 55)
        tail_threshold = params.get('tail_threshold', 2.5)
        hedge_threshold = params.get('hedge_threshold', 0.3)
        
        returns = data['close'].pct_change()
        
        # 1. Tail Events (extreme returns)
        returns_mean = returns.rolling(window=tail_period).mean()
        returns_std = returns.rolling(window=tail_period).std()
        
        z_score = (returns - returns_mean) / (returns_std + 1e-10)
        tail_event = (abs(z_score) > tail_threshold).astype(int)
        
        # 2. Tail Frequency (how often tail events occur)
        tail_frequency = tail_event.rolling(window=tail_period).sum() / tail_period
        
        # 3. Left Tail Risk (negative extreme events)
        left_tail_event = (z_score < -tail_threshold).astype(int)
        left_tail_frequency = left_tail_event.rolling(window=tail_period).sum() / tail_period
        
        # 4. Right Tail (positive extremes)
        right_tail_event = (z_score > tail_threshold).astype(int)
        right_tail_frequency = right_tail_event.rolling(window=tail_period).sum() / tail_period
        
        # 5. Tail Risk Score (probability of extreme event)
        # Based on recent volatility and tail frequency
        volatility = returns_std
        vol_percentile = volatility.rolling(window=tail_period * 2).rank(pct=True)
        
        tail_risk_score = (vol_percentile * 0.6 + tail_frequency * 0.4)
        
        # 6. Skewness (asymmetry of distribution)
        skewness = returns.rolling(window=tail_period).skew()
        
        # 7. Kurtosis (fat tails)
        kurtosis = returns.rolling(window=tail_period).kurt()
        excess_kurtosis = kurtosis - 3  # Normal distribution has kurtosis of 3
        
        # 8. Fat Tail Indicator (high kurtosis)
        fat_tails = (excess_kurtosis > 2).astype(int)
        
        # 9. Hedge Signal (when tail risk is elevated)
        hedge_signal = (
            (tail_risk_score > hedge_threshold) |
            (fat_tails == 1) |
            (left_tail_frequency > 0.05)
        ).astype(int)
        
        # 10. Optimal Conditions (low tail risk)
        optimal_conditions = (
            (tail_risk_score < hedge_threshold) &
            (fat_tails == 0) &
            (tail_frequency < 0.1)
        ).astype(int)
        
        result = pd.DataFrame({
            'z_score': z_score,
            'tail_event': tail_event,
            'tail_frequency': tail_frequency,
            'left_tail_frequency': left_tail_frequency,
            'right_tail_frequency': right_tail_frequency,
            'tail_risk_score': tail_risk_score,
            'skewness': skewness,
            'excess_kurtosis': excess_kurtosis,
            'fat_tails': fat_tails,
            'hedge_signal': hedge_signal,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['tail_risk_score'] < 0.3) &
            (result['hedge_signal'] == 0)
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
        signal_strength = (1.0 - result['tail_risk_score']).clip(0, 1)
        
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
            (result['tail_risk_score'] < 0.3) &
            (result['hedge_signal'] == 0)
        )
        
        exits = (
            (result['hedge_signal'] == 1) |
            (result['tail_event'] == 1) |
            (result['tail_risk_score'] > 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['hedge_signal'] == 1] = 'hedge_activated'
        exit_reason[result['tail_event'] == 1] = 'tail_event_detected'
        
        signal_strength = (1.0 - result['tail_risk_score']).clip(0, 1)
        
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
            'tail_z_score': result['z_score'],
            'tail_event': result['tail_event'],
            'tail_frequency': result['tail_frequency'],
            'tail_left_freq': result['left_tail_frequency'],
            'tail_right_freq': result['right_tail_frequency'],
            'tail_risk_score': result['tail_risk_score'],
            'tail_skewness': result['skewness'],
            'tail_excess_kurtosis': result['excess_kurtosis'],
            'tail_fat_tails': result['fat_tails'],
            'tail_hedge_signal': result['hedge_signal'],
            'tail_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'tail_period': [34, 55, 89],
            'tail_threshold': [2.0, 2.5, 3.0],
            'hedge_threshold': [0.25, 0.30, 0.35],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
