"""
569 - Neural Plasticity Indicator
Ultimate Master Indicator: Brain-inspired adaptive learning and pattern recognition
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class NeuralPlasticityIndicator:
    """
    Neural Plasticity Indicator - Brain-inspired market learning
    
    Features:
    - Synaptic strength modeling
    - Learning rate adaptation
    - Memory consolidation
    - Pattern recognition plasticity
    - Neural network health
    """
    
    def __init__(self):
        self.name = "Neural Plasticity Indicator"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate neural plasticity score"""
        
        # Parameters
        neural_period = params.get('neural_period', 50)
        learning_period = params.get('learning_period', 20)
        memory_period = params.get('memory_period', 100)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Synaptic Strength Modeling
        returns = close.pct_change()
        
        # Connection strength (correlation persistence)
        price_momentum = returns.rolling(learning_period).mean()
        volume_momentum = volume.pct_change().rolling(learning_period).mean()
        
        synaptic_correlation = price_momentum.rolling(neural_period).corr(volume_momentum)
        synaptic_strength = abs(synaptic_correlation)
        
        # Synaptic weight (importance)
        signal_amplitude = abs(returns).rolling(learning_period).mean()
        noise_level = returns.rolling(learning_period).std()
        signal_to_noise = signal_amplitude / (noise_level + 1e-10)
        synaptic_weight = np.tanh(signal_to_noise)
        
        # Combined synaptic score
        synaptic_score = (synaptic_strength + synaptic_weight) / 2
        
        # 2. Learning Rate Adaptation
        # Error-based learning (prediction vs reality)
        predicted_price = close.rolling(learning_period).mean()
        prediction_error = abs(close - predicted_price) / close
        
        # Learning rate (higher error = faster learning)
        base_learning_rate = prediction_error / (prediction_error.rolling(neural_period).mean() + 1e-10)
        
        # Adaptive learning rate (decreases with confidence)
        confidence = 1 / (1 + prediction_error.rolling(learning_period).std())
        adaptive_learning_rate = base_learning_rate * (1 - confidence)
        
        # Learning efficiency
        error_reduction = prediction_error.diff(learning_period)
        learning_efficiency = -np.tanh(error_reduction * 100)  # Negative error change is good
        
        learning_rate_score = (
            0.5 * np.tanh(adaptive_learning_rate) +
            0.5 * learning_efficiency
        )
        
        # 3. Memory Consolidation
        # Short-term memory (recent patterns)
        stm_pattern = returns.rolling(learning_period).apply(
            lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1] if len(x) > 1 else 0
        )
        
        # Long-term memory (historical patterns)
        ltm_pattern = returns.rolling(memory_period).apply(
            lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1] if len(x) > 1 else 0
        )
        
        # Memory consolidation (STM -> LTM transfer)
        memory_alignment = stm_pattern.rolling(neural_period).corr(ltm_pattern)
        consolidation_strength = abs(memory_alignment)
        
        # Memory retention
        pattern_persistence = stm_pattern.rolling(neural_period).std()
        memory_retention = 1 / (1 + pattern_persistence)
        
        memory_consolidation = (consolidation_strength + memory_retention) / 2
        
        # 4. Pattern Recognition Plasticity
        # Pattern detection sensitivity
        pattern_strength = abs(stm_pattern)
        detection_threshold = pattern_strength.rolling(neural_period).quantile(0.7)
        detection_sensitivity = (pattern_strength > detection_threshold).astype(float)
        
        # Pattern generalization
        pattern_variance = stm_pattern.rolling(learning_period).std()
        generalization_ability = 1 / (1 + pattern_variance)
        
        # Pattern discrimination
        unique_patterns = returns.rolling(neural_period).apply(
            lambda x: len(np.unique(np.sign(x))) / len(x) if len(x) > 0 else 0
        )
        discrimination_ability = unique_patterns
        
        recognition_plasticity = (
            0.4 * detection_sensitivity +
            0.3 * generalization_ability +
            0.3 * discrimination_ability
        )
        
        # 5. Neural Network Health
        # Network stability
        synaptic_volatility = synaptic_score.rolling(neural_period).std()
        network_stability = 1 / (1 + synaptic_volatility)
        
        # Information flow
        price_change_rate = abs(returns).rolling(learning_period).mean()
        information_flow = price_change_rate / (price_change_rate.rolling(neural_period).max() + 1e-10)
        
        # Network resilience (recovery from shocks)
        shock_magnitude = abs(returns) > returns.rolling(neural_period).quantile(0.95)
        recovery_time = shock_magnitude.rolling(learning_period).sum()
        network_resilience = 1 / (1 + recovery_time / learning_period)
        
        neural_health = (
            0.4 * network_stability +
            0.3 * information_flow +
            0.3 * network_resilience
        )
        
        # 6. Neural Plasticity Score
        plasticity_score = (
            0.25 * synaptic_score +
            0.20 * learning_rate_score +
            0.20 * memory_consolidation +
            0.20 * recognition_plasticity +
            0.15 * neural_health
        )
        
        # 7. Plasticity State
        plasticity_state = pd.Series(0, index=data.index)
        plasticity_state[(plasticity_score > 0.7) & (learning_rate_score > 0.5)] = 3  # Highly plastic
        plasticity_state[(plasticity_score > 0.5) & (plasticity_score <= 0.7)] = 2  # Adaptive
        plasticity_state[(plasticity_score > 0.3) & (plasticity_score <= 0.5)] = 1  # Stable
        plasticity_state[plasticity_score <= 0.3] = 0  # Rigid
        
        # 8. Learning Progress
        plasticity_improvement = plasticity_score.diff(learning_period)
        learning_progress = np.tanh(plasticity_improvement * 10)
        
        result = pd.DataFrame(index=data.index)
        result['plasticity_score'] = plasticity_score
        result['synaptic_score'] = synaptic_score
        result['learning_rate_score'] = learning_rate_score
        result['memory_consolidation'] = memory_consolidation
        result['recognition_plasticity'] = recognition_plasticity
        result['neural_health'] = neural_health
        result['plasticity_state'] = plasticity_state
        result['learning_progress'] = learning_progress
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: High plasticity with strong learning
        entries = (
            (indicator['plasticity_score'] > 0.6) &
            (indicator['learning_rate_score'] > 0.5) &
            (indicator['neural_health'] > 0.6) &
            (indicator['plasticity_state'] >= 2)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 100)
        sl_pips = params.get('sl_pips', 40)
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
        
        signal_strength = indicator['plasticity_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on plasticity decline"""
        
        indicator = self.calculate(data, params)
        
        # Entry: High plasticity
        entries = (
            (indicator['plasticity_score'] > 0.6) &
            (indicator['learning_rate_score'] > 0.5) &
            (indicator['neural_health'] > 0.6) &
            (indicator['plasticity_state'] >= 2)
        )
        
        # Exit: Plasticity decline or health deterioration
        exits = (
            (indicator['plasticity_score'] < 0.3) |
            (indicator['neural_health'] < 0.3) |
            (indicator['plasticity_state'] <= 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['plasticity_score'] < 0.3)] = 'plasticity_loss'
        exit_reason[exits & (indicator['neural_health'] < 0.3)] = 'health_deterioration'
        exit_reason[exits & (indicator['plasticity_state'] <= 0)] = 'rigidity_onset'
        
        signal_strength = indicator['plasticity_score'].clip(0, 1)
        
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
        features['plasticity_score'] = indicator['plasticity_score']
        features['synaptic_score'] = indicator['synaptic_score']
        features['learning_rate_score'] = indicator['learning_rate_score']
        features['memory_consolidation'] = indicator['memory_consolidation']
        features['recognition_plasticity'] = indicator['recognition_plasticity']
        features['neural_health'] = indicator['neural_health']
        features['plasticity_state'] = indicator['plasticity_state']
        features['learning_progress'] = indicator['learning_progress']
        
        # Additional features
        features['plasticity_momentum'] = indicator['plasticity_score'].diff(5)
        features['health_trend'] = indicator['neural_health'].rolling(10).mean()
        features['learning_stability'] = indicator['learning_rate_score'].rolling(15).std()
        features['memory_strength'] = indicator['memory_consolidation'].rolling(20).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'neural_period': [40, 50, 60, 75, 100],
            'learning_period': [15, 20, 25, 30, 40],
            'memory_period': [75, 100, 125, 150, 200],
            'tp_pips': [60, 75, 100, 125, 150],
            'sl_pips': [25, 30, 40, 50, 60]
        }
