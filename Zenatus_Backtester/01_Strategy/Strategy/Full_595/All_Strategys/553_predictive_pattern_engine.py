"""
553_predictive_pattern_engine.py
=================================
Indicator: Predictive Pattern Engine
Category: Grand Finale / Pattern Prediction
Complexity: Elite

Description:
-----------
Advanced pattern recognition engine that predicts future price movements based
on historical pattern matching. Uses template matching and sequence prediction
to forecast market behavior.

Key Features:
- Pattern template matching
- Sequence prediction
- Forecast accuracy tracking
- Predictive confidence scoring

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_PredictivePatternEngine:
    """
    Predictive Pattern Engine
    
    Predicts future patterns based on historical matching.
    """
    
    def __init__(self):
        self.name = "Predictive Pattern Engine"
        self.version = "1.0.0"
        self.category = "Grand Finale"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Predictive Pattern metrics
        
        Parameters:
        - pattern_length: Length of pattern to match (default: 13)
        - prediction_horizon: Horizon for prediction (default: 5)
        - match_threshold: Threshold for pattern match (default: 0.8)
        """
        pattern_length = params.get('pattern_length', 13)
        prediction_horizon = params.get('prediction_horizon', 5)
        match_threshold = params.get('match_threshold', 0.8)
        
        returns = data['close'].pct_change()
        
        # Normalize returns for pattern matching
        normalized_returns = (returns - returns.rolling(window=pattern_length * 2).mean()) / \
                            (returns.rolling(window=pattern_length * 2).std() + 1e-10)
        
        # 1. Pattern Matching Score
        pattern_match_score = pd.Series(0.0, index=data.index)
        
        for i in range(pattern_length * 3, len(data)):
            current_pattern = normalized_returns.iloc[i-pattern_length:i].values
            
            # Find best matching historical pattern
            best_match = 0.0
            
            for j in range(pattern_length * 2, i - pattern_length * 2):
                historical_pattern = normalized_returns.iloc[j-pattern_length:j].values
                
                if len(current_pattern) == len(historical_pattern):
                    # Correlation as similarity measure
                    corr = np.corrcoef(current_pattern, historical_pattern)[0, 1]
                    if np.isfinite(corr) and abs(corr) > best_match:
                        best_match = abs(corr)
            
            pattern_match_score.iloc[i] = best_match
        
        # 2. Pattern Found (strong match exists)
        pattern_found = (pattern_match_score > match_threshold).astype(int)
        
        # 3. Predicted Direction (based on what happened after historical match)
        predicted_direction = pd.Series(0, index=data.index)
        
        for i in range(pattern_length * 3, len(data) - prediction_horizon):
            if pattern_match_score.iloc[i] > match_threshold:
                # Find the historical match
                current_pattern = normalized_returns.iloc[i-pattern_length:i].values
                
                best_match_idx = 0
                best_corr = 0
                
                for j in range(pattern_length * 2, i - pattern_length * 2):
                    historical_pattern = normalized_returns.iloc[j-pattern_length:j].values
                    
                    if len(current_pattern) == len(historical_pattern):
                        corr = np.corrcoef(current_pattern, historical_pattern)[0, 1]
                        if np.isfinite(corr) and abs(corr) > best_corr:
                            best_corr = abs(corr)
                            best_match_idx = j
                
                # Predict based on what happened after historical match
                if best_match_idx > 0 and best_match_idx + prediction_horizon < i:
                    future_return = returns.iloc[best_match_idx:best_match_idx + prediction_horizon].sum()
                    predicted_direction.iloc[i] = np.sign(future_return)
        
        # 4. Prediction Confidence (match quality)
        prediction_confidence = pattern_match_score
        
        # 5. Forecast Accuracy (how often predictions are correct)
        actual_direction = np.sign(returns.rolling(window=prediction_horizon).sum().shift(-prediction_horizon))
        prediction_correct = (predicted_direction == actual_direction).astype(float)
        forecast_accuracy = prediction_correct.rolling(window=pattern_length * 2).mean()
        
        # 6. Predictive Power (accuracy * confidence)
        predictive_power = forecast_accuracy * prediction_confidence
        
        # 7. Optimal Predictive Conditions
        optimal_conditions = (
            (pattern_found == 1) &
            (forecast_accuracy > 0.6) &
            (predictive_power > 0.5) &
            (predicted_direction != 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'pattern_match_score': pattern_match_score,
            'pattern_found': pattern_found,
            'predicted_direction': predicted_direction,
            'prediction_confidence': prediction_confidence,
            'forecast_accuracy': forecast_accuracy,
            'predictive_power': predictive_power,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['predicted_direction'] > 0) &
            (result['forecast_accuracy'] > 0.6)
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
        signal_strength = result['predictive_power'].clip(0, 1)
        
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
            (result['predicted_direction'] > 0) &
            (result['forecast_accuracy'] > 0.6)
        )
        
        exits = (
            (result['predicted_direction'] < 0) |
            (result['pattern_found'] == 0) |
            (result['forecast_accuracy'] < 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['predicted_direction'] < 0] = 'prediction_reversed'
        exit_reason[result['pattern_found'] == 0] = 'pattern_lost'
        
        signal_strength = result['predictive_power'].clip(0, 1)
        
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
            'pred_match_score': result['pattern_match_score'],
            'pred_pattern_found': result['pattern_found'],
            'pred_direction': result['predicted_direction'],
            'pred_confidence': result['prediction_confidence'],
            'pred_accuracy': result['forecast_accuracy'],
            'pred_power': result['predictive_power'],
            'pred_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'pattern_length': [8, 13, 21],
            'prediction_horizon': [3, 5, 8],
            'match_threshold': [0.7, 0.8, 0.9],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
