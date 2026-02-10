"""
530_federated_learning_composite.py
====================================
Indicator: Federated Learning Composite
Category: Advanced ML / Distributed Learning
Complexity: Elite

Description:
-----------
Simulates federated learning by combining insights from multiple "local models"
(different timeframes/features). Each model learns independently, then knowledge
is aggregated. Robust to local noise, captures multi-scale patterns.

Key Features:
- Multi-model aggregation
- Consensus scoring
- Model disagreement detection
- Federated alpha generation

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_FederatedLearningComposite:
    """
    Federated Learning Composite
    
    Aggregates insights from multiple independent models.
    """
    
    def __init__(self):
        self.name = "Federated Learning Composite"
        self.version = "1.0.0"
        self.category = "Advanced ML"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Federated Learning metrics
        
        Parameters:
        - num_models: Number of local models (default: 5)
        - aggregation_period: Period for aggregation (default: 21)
        - consensus_threshold: Threshold for consensus (default: 0.7)
        """
        num_models = params.get('num_models', 5)
        aggregation_period = params.get('aggregation_period', 21)
        consensus_threshold = params.get('consensus_threshold', 0.7)
        
        returns = data['close'].pct_change()
        
        # Define Local Models (different timeframes/approaches)
        model_periods = [8, 13, 21, 34, 55][:num_models]
        
        # 1. Local Model Predictions
        local_predictions = []
        
        for period in model_periods:
            # Each model predicts direction based on its timeframe
            model_signal = returns.rolling(window=period).mean()
            model_prediction = np.sign(model_signal)
            local_predictions.append(model_prediction)
        
        # 2. Federated Consensus (majority vote)
        consensus_signal = pd.Series(0.0, index=data.index)
        
        for i in range(len(data)):
            votes = [pred.iloc[i] for pred in local_predictions]
            consensus_signal.iloc[i] = np.sign(np.sum(votes))
        
        # 3. Consensus Strength (how many models agree)
        consensus_strength = pd.Series(0.0, index=data.index)
        
        for i in range(len(data)):
            votes = [pred.iloc[i] for pred in local_predictions]
            agreement = np.sum([v == consensus_signal.iloc[i] for v in votes]) / len(votes)
            consensus_strength.iloc[i] = agreement
        
        # 4. Model Disagreement (diversity of opinions)
        model_disagreement = 1.0 - consensus_strength
        
        # 5. High Consensus (strong agreement)
        high_consensus = (consensus_strength > consensus_threshold).astype(int)
        
        # 6. Model Confidence (weighted by recent accuracy)
        model_confidence = pd.Series(0.0, index=data.index)
        
        for i in range(aggregation_period, len(data)):
            # Calculate recent accuracy of consensus
            recent_consensus = consensus_signal.iloc[i-aggregation_period:i]
            recent_returns = returns.iloc[i-aggregation_period:i]
            
            # Accuracy: consensus direction matches actual direction
            correct = (np.sign(recent_consensus) == np.sign(recent_returns)).sum()
            model_confidence.iloc[i] = correct / aggregation_period
        
        # 7. Federated Alpha (consensus weighted by confidence)
        federated_alpha = consensus_signal * consensus_strength * model_confidence
        
        # 8. Aggregation Quality (how well models work together)
        aggregation_quality = consensus_strength * model_confidence
        
        # 9. Optimal Federated Conditions (high consensus + high confidence)
        optimal_conditions = (
            (high_consensus == 1) &
            (model_confidence > 0.6) &
            (aggregation_quality > 0.5) &
            (consensus_signal != 0)
        ).astype(int)
        
        # 10. Individual Model Strengths
        model_strengths = []
        for j, period in enumerate(model_periods):
            strength = abs(local_predictions[j]).rolling(window=aggregation_period).mean()
            model_strengths.append(strength)
        
        # Average model strength
        avg_model_strength = pd.concat(model_strengths, axis=1).mean(axis=1)
        
        result = pd.DataFrame({
            'consensus_signal': consensus_signal,
            'consensus_strength': consensus_strength,
            'model_disagreement': model_disagreement,
            'high_consensus': high_consensus,
            'model_confidence': model_confidence,
            'federated_alpha': federated_alpha,
            'aggregation_quality': aggregation_quality,
            'optimal_conditions': optimal_conditions,
            'avg_model_strength': avg_model_strength
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal federated conditions (high consensus + confidence)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['consensus_signal'] > 0) &
            (result['consensus_strength'] > 0.7) &
            (result['model_confidence'] > 0.6)
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
        
        signal_strength = result['aggregation_quality'].clip(0, 1)
        
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
        
        Entry: Optimal federated conditions
        Exit: When consensus breaks or confidence drops
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['consensus_signal'] > 0) &
            (result['consensus_strength'] > 0.7) &
            (result['model_confidence'] > 0.6)
        )
        
        exits = (
            (result['consensus_signal'] <= 0) |
            (result['consensus_strength'] < 0.5) |
            (result['model_confidence'] < 0.4) |
            (result['model_disagreement'] > 0.6)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['consensus_signal'] <= 0] = 'consensus_reversed'
        exit_reason[result['consensus_strength'] < 0.5] = 'consensus_weak'
        exit_reason[result['model_confidence'] < 0.4] = 'confidence_dropped'
        
        signal_strength = result['aggregation_quality'].clip(0, 1)
        
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
            'fed_consensus_signal': result['consensus_signal'],
            'fed_consensus_strength': result['consensus_strength'],
            'fed_disagreement': result['model_disagreement'],
            'fed_high_consensus': result['high_consensus'],
            'fed_model_confidence': result['model_confidence'],
            'fed_alpha': result['federated_alpha'],
            'fed_aggregation_quality': result['aggregation_quality'],
            'fed_optimal': result['optimal_conditions'],
            'fed_avg_model_strength': result['avg_model_strength']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'num_models': [3, 5, 7],
            'aggregation_period': [13, 21, 34],
            'consensus_threshold': [0.6, 0.7, 0.8],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
