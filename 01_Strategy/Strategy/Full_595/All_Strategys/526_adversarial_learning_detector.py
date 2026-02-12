"""
526_adversarial_learning_detector.py
=====================================
Indicator: Adversarial Learning Detector
Category: Advanced ML / Adversarial Analysis
Complexity: Elite

Description:
-----------
Detects adversarial market conditions where normal patterns fail. Uses
adversarial learning concepts to identify when market behavior deviates
from learned patterns, signaling potential regime changes or manipulation.

Key Features:
- Adversarial pattern detection
- Model confidence measurement
- Anomaly scoring
- Robustness testing

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_AdversarialLearningDetector:
    """
    Adversarial Learning Detector
    
    Detects adversarial conditions where patterns fail.
    """
    
    def __init__(self):
        self.name = "Adversarial Learning Detector"
        self.version = "1.0.0"
        self.category = "Advanced ML"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Adversarial Learning metrics
        
        Parameters:
        - learning_period: Period for pattern learning (default: 55)
        - adversarial_period: Period for adversarial detection (default: 21)
        - anomaly_threshold: Threshold for anomaly detection (default: 2.5)
        """
        learning_period = params.get('learning_period', 55)
        adversarial_period = params.get('adversarial_period', 21)
        anomaly_threshold = params.get('anomaly_threshold', 2.5)
        
        returns = data['close'].pct_change()
        
        # 1. Expected Pattern (learned from historical data)
        expected_return = returns.rolling(window=learning_period).mean()
        expected_volatility = returns.rolling(window=learning_period).std()
        
        # 2. Actual vs Expected Deviation
        pattern_deviation = (returns - expected_return) / (expected_volatility + 1e-10)
        
        # 3. Adversarial Score (how much actual deviates from expected)
        adversarial_score = abs(pattern_deviation)
        
        # 4. Adversarial Event (significant deviation)
        adversarial_event = (adversarial_score > anomaly_threshold).astype(int)
        
        # 5. Model Confidence (inverse of deviation)
        model_confidence = 1.0 / (adversarial_score + 1.0)
        
        # 6. Pattern Stability (consistency of patterns)
        pattern_stability = 1.0 / (expected_volatility.rolling(window=adversarial_period).std() + 1e-10)
        pattern_stability_normalized = pattern_stability / pattern_stability.rolling(window=50).mean()
        
        # 7. Adversarial Frequency (how often adversarial events occur)
        adversarial_frequency = adversarial_event.rolling(window=adversarial_period).sum() / adversarial_period
        
        # 8. Robustness Score (low adversarial frequency = robust)
        robustness_score = 1.0 - adversarial_frequency
        
        # 9. Regime Shift Detection (sustained adversarial behavior)
        regime_shift = (
            (adversarial_frequency > 0.3) &
            (pattern_stability_normalized < 0.7)
        ).astype(int)
        
        # 10. Optimal Trading Conditions (high confidence + robust + stable)
        optimal_conditions = (
            (model_confidence > 0.7) &
            (robustness_score > 0.7) &
            (pattern_stability_normalized > 1.2) &
            (adversarial_event == 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'expected_return': expected_return,
            'pattern_deviation': pattern_deviation,
            'adversarial_score': adversarial_score,
            'adversarial_event': adversarial_event,
            'model_confidence': model_confidence,
            'pattern_stability': pattern_stability_normalized,
            'adversarial_frequency': adversarial_frequency,
            'robustness_score': robustness_score,
            'regime_shift': regime_shift,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal conditions (high confidence + robust)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['model_confidence'] > 0.7) &
            (result['robustness_score'] > 0.7) &
            (result['regime_shift'] == 0)
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
        
        signal_strength = result['model_confidence'].clip(0, 1)
        
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
        
        Entry: Optimal conditions
        Exit: When adversarial event or regime shift
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['model_confidence'] > 0.7) &
            (result['robustness_score'] > 0.7) &
            (result['regime_shift'] == 0)
        )
        
        exits = (
            (result['adversarial_event'] == 1) |
            (result['regime_shift'] == 1) |
            (result['model_confidence'] < 0.5) |
            (result['robustness_score'] < 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['adversarial_event'] == 1] = 'adversarial_detected'
        exit_reason[result['regime_shift'] == 1] = 'regime_shift'
        exit_reason[result['model_confidence'] < 0.5] = 'confidence_low'
        
        signal_strength = result['model_confidence'].clip(0, 1)
        
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
            'adv_expected_return': result['expected_return'],
            'adv_pattern_deviation': result['pattern_deviation'],
            'adv_score': result['adversarial_score'],
            'adv_event': result['adversarial_event'],
            'adv_model_confidence': result['model_confidence'],
            'adv_pattern_stability': result['pattern_stability'],
            'adv_frequency': result['adversarial_frequency'],
            'adv_robustness': result['robustness_score'],
            'adv_regime_shift': result['regime_shift'],
            'adv_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'learning_period': [34, 55, 89],
            'adversarial_period': [13, 21, 34],
            'anomaly_threshold': [2.0, 2.5, 3.0],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
