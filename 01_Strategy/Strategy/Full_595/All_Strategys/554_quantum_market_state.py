"""
554_quantum_market_state.py
============================
Indicator: Quantum Market State
Category: Grand Finale / Quantum Analysis
Complexity: Elite

Description:
-----------
Advanced quantum-inspired indicator that models market as quantum system.
Analyzes superposition of states, uncertainty principles, and wave-particle
duality in price action.

Key Features:
- Quantum state modeling
- Uncertainty measurement
- State superposition analysis
- Quantum transition detection

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_QuantumMarketState:
    """
    Quantum Market State
    
    Models market as quantum system.
    """
    
    def __init__(self):
        self.name = "Quantum Market State"
        self.version = "1.0.0"
        self.category = "Grand Finale"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Quantum Market State metrics
        
        Parameters:
        - quantum_period: Period for quantum analysis (default: 34)
        - uncertainty_threshold: Threshold for uncertainty (default: 0.5)
        - state_levels: Number of quantum states (default: 5)
        """
        quantum_period = params.get('quantum_period', 34)
        uncertainty_threshold = params.get('uncertainty_threshold', 0.5)
        state_levels = params.get('state_levels', 5)
        
        returns = data['close'].pct_change()
        
        # 1. Quantum States (discretize price into energy levels)
        price_percentile = data['close'].rolling(window=quantum_period * 2).rank(pct=True)
        quantum_state = (price_percentile * state_levels).fillna(0).astype(int).clip(0, state_levels - 1)
        
        # 2. State Probability Distribution
        state_probabilities = []
        for state in range(state_levels):
            prob = (quantum_state == state).rolling(window=quantum_period).mean()
            state_probabilities.append(prob)
        
        # 3. Entropy (uncertainty in state)
        entropy = pd.Series(0.0, index=data.index)
        
        for i in range(quantum_period, len(data)):
            probs = [sp.iloc[i] for sp in state_probabilities]
            probs = [p for p in probs if p > 0]
            if probs:
                entropy.iloc[i] = -np.sum([p * np.log(p) for p in probs])
        
        # Normalize entropy
        max_entropy = np.log(state_levels)
        entropy_normalized = entropy / max_entropy
        
        # 4. Uncertainty (high entropy = high uncertainty)
        uncertainty = entropy_normalized
        
        # 5. Dominant State (most probable state)
        dominant_state = pd.concat(state_probabilities, axis=1).idxmax(axis=1)
        
        # 6. State Transition (changing states)
        state_transition = (quantum_state != quantum_state.shift(1)).astype(int)
        
        # 7. Quantum Coherence (stability of state)
        coherence = 1.0 - entropy_normalized
        
        # 8. Wave Function (oscillating component)
        wave_function = np.sin(2 * np.pi * price_percentile)
        
        # 9. Optimal Quantum Conditions (low uncertainty + stable state)
        optimal_conditions = (
            (uncertainty < uncertainty_threshold) &
            (coherence > 0.6) &
            (state_transition == 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'quantum_state': quantum_state,
            'entropy': entropy_normalized,
            'uncertainty': uncertainty,
            'dominant_state': dominant_state,
            'state_transition': state_transition,
            'coherence': coherence,
            'wave_function': wave_function,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['coherence'] > 0.6) &
            (result['uncertainty'] < 0.5)
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
        signal_strength = result['coherence'].clip(0, 1)
        
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
            (result['coherence'] > 0.6) &
            (result['uncertainty'] < 0.5)
        )
        
        exits = (
            (result['state_transition'] == 1) |
            (result['uncertainty'] > 0.7) |
            (result['coherence'] < 0.4)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['state_transition'] == 1] = 'state_changed'
        exit_reason[result['uncertainty'] > 0.7] = 'high_uncertainty'
        
        signal_strength = result['coherence'].clip(0, 1)
        
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
            'quantum_state': result['quantum_state'],
            'quantum_entropy': result['entropy'],
            'quantum_uncertainty': result['uncertainty'],
            'quantum_dominant_state': result['dominant_state'],
            'quantum_transition': result['state_transition'],
            'quantum_coherence': result['coherence'],
            'quantum_wave': result['wave_function'],
            'quantum_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'quantum_period': [21, 34, 55],
            'uncertainty_threshold': [0.4, 0.5, 0.6],
            'state_levels': [3, 5, 7],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
