"""
574 - Absolute Certainty Engine
Ultimate Master Indicator: Measures absolute certainty in market direction
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class AbsoluteCertaintyEngine:
    """
    Absolute Certainty Engine - Quantifies market certainty levels
    
    Features:
    - Certainty quantification
    - Uncertainty measurement
    - Probability distribution estimation
    - Confidence interval calculation
    - Decision clarity assessment
    """
    
    def __init__(self):
        self.name = "Absolute Certainty Engine"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate absolute certainty score"""
        
        # Parameters
        certainty_period = params.get('certainty_period', 60)
        confidence_period = params.get('confidence_period', 40)
        probability_period = params.get('probability_period', 30)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Certainty Quantification
        returns = close.pct_change()
        
        # Directional certainty (consistency of direction)
        direction = np.sign(returns)
        directional_consistency = abs(direction.rolling(certainty_period).sum()) / certainty_period
        
        # Magnitude certainty (consistency of magnitude)
        magnitude = abs(returns)
        magnitude_mean = magnitude.rolling(certainty_period).mean()
        magnitude_std = magnitude.rolling(certainty_period).std()
        magnitude_certainty = magnitude_mean / (magnitude_std + 1e-10)
        magnitude_certainty = np.tanh(magnitude_certainty)
        
        # Trend certainty
        trend_strength = close.rolling(certainty_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        
        certainty_score = (
            0.4 * directional_consistency +
            0.3 * magnitude_certainty +
            0.3 * trend_strength
        )
        
        # 2. Uncertainty Measurement
        # Price uncertainty (volatility)
        price_uncertainty = returns.rolling(confidence_period).std()
        price_uncertainty_normalized = price_uncertainty / price_uncertainty.rolling(certainty_period).max()
        
        # Prediction uncertainty
        predicted_price = close.rolling(confidence_period).mean()
        prediction_error = abs(close - predicted_price) / close
        prediction_uncertainty = prediction_error.rolling(confidence_period).mean()
        
        # Information uncertainty (entropy)
        price_bins = pd.cut(returns, bins=10, labels=False, duplicates='drop')
        information_entropy = price_bins.rolling(confidence_period).apply(
            lambda x: -np.sum((np.bincount(x.dropna().astype(int)) / len(x)) * 
                             np.log2(np.bincount(x.dropna().astype(int)) / len(x) + 1e-10))
            if len(x) > 0 else 0
        )
        information_entropy_normalized = information_entropy / np.log2(10)
        
        uncertainty_score = (
            0.4 * price_uncertainty_normalized +
            0.3 * prediction_uncertainty +
            0.3 * information_entropy_normalized
        )
        
        # 3. Probability Distribution Estimation
        # Estimate probability of upward movement
        historical_up_prob = (returns > 0).rolling(probability_period).mean()
        
        # Adjust by current momentum
        momentum = returns.rolling(probability_period).mean()
        momentum_factor = np.tanh(momentum * 100) * 0.5 + 0.5  # 0 to 1
        
        # Adjust by volatility regime
        volatility_regime = price_uncertainty_normalized
        volatility_adjustment = 1 - volatility_regime * 0.3
        
        probability_up = historical_up_prob * momentum_factor * volatility_adjustment
        probability_up = probability_up.clip(0, 1)
        
        # Probability certainty (how confident in the probability)
        prob_variance = probability_up.rolling(probability_period).std()
        probability_certainty = 1 / (1 + prob_variance)
        
        # 4. Confidence Interval Calculation
        # Calculate confidence bounds
        mean_return = returns.rolling(confidence_period).mean()
        std_return = returns.rolling(confidence_period).std()
        
        # 95% confidence interval
        confidence_lower = mean_return - 1.96 * std_return
        confidence_upper = mean_return + 1.96 * std_return
        confidence_width = confidence_upper - confidence_lower
        
        # Narrow confidence interval = high certainty
        confidence_interval_score = 1 / (1 + abs(confidence_width))
        
        # Current position within confidence interval
        current_return = returns
        interval_position = (current_return - confidence_lower) / (confidence_width + 1e-10)
        interval_position = interval_position.clip(0, 1)
        
        # 5. Decision Clarity Assessment
        # Signal clarity (strong vs weak signals)
        signal_strength = abs(certainty_score - 0.5) * 2  # 0 to 1
        
        # Decision consistency
        decision = (certainty_score > 0.5).astype(int)
        decision_changes = (decision != decision.shift()).astype(int)
        decision_stability = 1 - decision_changes.rolling(confidence_period).mean()
        
        # Action clarity (clear entry/exit points)
        action_threshold = 0.7
        clear_action = ((certainty_score > action_threshold) | (certainty_score < 1 - action_threshold)).astype(float)
        action_clarity = clear_action.rolling(probability_period).mean()
        
        decision_clarity = (
            0.4 * signal_strength +
            0.3 * decision_stability +
            0.3 * action_clarity
        )
        
        # 6. Absolute Certainty Score
        absolute_certainty = (
            0.30 * certainty_score +
            0.25 * (1 - uncertainty_score) +
            0.20 * probability_certainty +
            0.15 * confidence_interval_score +
            0.10 * decision_clarity
        )
        
        # 7. Certainty Level
        certainty_level = pd.Series(0, index=data.index)
        certainty_level[(absolute_certainty > 0.8) & (uncertainty_score < 0.2)] = 4  # Absolute certainty
        certainty_level[(absolute_certainty > 0.6) & (absolute_certainty <= 0.8)] = 3  # High certainty
        certainty_level[(absolute_certainty > 0.4) & (absolute_certainty <= 0.6)] = 2  # Moderate
        certainty_level[(absolute_certainty > 0.2) & (absolute_certainty <= 0.4)] = 1  # Low
        certainty_level[absolute_certainty <= 0.2] = 0  # No certainty
        
        # 8. Certainty Direction
        certainty_direction = np.sign(mean_return) * absolute_certainty
        
        result = pd.DataFrame(index=data.index)
        result['absolute_certainty'] = absolute_certainty
        result['certainty_score'] = certainty_score
        result['uncertainty_score'] = uncertainty_score
        result['probability_up'] = probability_up
        result['probability_certainty'] = probability_certainty
        result['confidence_interval_score'] = confidence_interval_score
        result['decision_clarity'] = decision_clarity
        result['certainty_level'] = certainty_level
        result['certainty_direction'] = certainty_direction
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Absolute certainty with clear direction
        entries = (
            (indicator['absolute_certainty'] > 0.75) &
            (indicator['certainty_direction'] > 0.5) &
            (indicator['uncertainty_score'] < 0.3) &
            (indicator['certainty_level'] >= 3)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 150)
        sl_pips = params.get('sl_pips', 60)
        pip_value = 0.0001
        
        # Manual TP/SL Exit Logic
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
        
        # Dummy levels
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        
        signal_strength = indicator['absolute_certainty'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on certainty loss"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Absolute certainty
        entries = (
            (indicator['absolute_certainty'] > 0.75) &
            (indicator['certainty_direction'] > 0.5) &
            (indicator['uncertainty_score'] < 0.3) &
            (indicator['certainty_level'] >= 3)
        )
        
        # Exit: Certainty loss or uncertainty spike
        exits = (
            (indicator['absolute_certainty'] < 0.3) |
            (indicator['uncertainty_score'] > 0.7) |
            (indicator['certainty_level'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['absolute_certainty'] < 0.3)] = 'certainty_loss'
        exit_reason[exits & (indicator['uncertainty_score'] > 0.7)] = 'uncertainty_spike'
        exit_reason[exits & (indicator['certainty_level'] <= 1)] = 'certainty_collapse'
        
        signal_strength = indicator['absolute_certainty'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extract ML features"""
        
        indicator = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        features['absolute_certainty'] = indicator['absolute_certainty']
        features['certainty_score'] = indicator['certainty_score']
        features['uncertainty_score'] = indicator['uncertainty_score']
        features['probability_up'] = indicator['probability_up']
        features['probability_certainty'] = indicator['probability_certainty']
        features['confidence_interval_score'] = indicator['confidence_interval_score']
        features['decision_clarity'] = indicator['decision_clarity']
        features['certainty_level'] = indicator['certainty_level']
        features['certainty_direction'] = indicator['certainty_direction']
        
        # Additional features
        features['certainty_momentum'] = indicator['absolute_certainty'].diff(5)
        features['uncertainty_trend'] = indicator['uncertainty_score'].rolling(10).mean()
        features['probability_stability'] = indicator['probability_certainty'].rolling(15).std()
        features['clarity_trend'] = indicator['decision_clarity'].rolling(20).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'certainty_period': [50, 60, 75, 100, 125],
            'confidence_period': [30, 40, 50, 60, 75],
            'probability_period': [20, 25, 30, 40, 50],
            'tp_pips': [100, 125, 150, 175, 200],
            'sl_pips': [40, 50, 60, 75, 100]
        }
