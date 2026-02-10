"""
582 - Primordial Chaos Order
Ultimate Master Indicator: Finds order within primordial market chaos
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class PrimordialChaosOrder:
    """
    Primordial Chaos Order - Order from chaos
    
    Features:
    - Chaos measurement
    - Order detection
    - Transition identification
    - Entropy analysis
    - Pattern emergence
    """
    
    def __init__(self):
        self.name = "Primordial Chaos Order"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate chaos-order score"""
        
        # Parameters
        chaos_period = params.get('chaos_period', 89)
        order_period = params.get('order_period', 55)
        transition_period = params.get('transition_period', 34)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Chaos Measurement
        # Lyapunov-like exponent
        divergence = abs(returns - returns.shift(1))
        chaos_level = divergence.rolling(chaos_period).mean() / (divergence.rolling(chaos_period).std() + 1e-10)
        chaos_level = np.tanh(chaos_level)
        
        # Entropy
        price_bins = pd.cut(returns, bins=10, labels=False, duplicates='drop')
        entropy = price_bins.rolling(transition_period).apply(
            lambda x: -np.sum((np.bincount(x.dropna().astype(int)) / len(x)) * 
                             np.log2(np.bincount(x.dropna().astype(int)) / len(x) + 1e-10))
            if len(x) > 0 else 0
        )
        entropy_normalized = entropy / np.log2(10)
        
        chaos_score = (chaos_level + entropy_normalized) / 2
        
        # 2. Order Detection
        # Trend as order
        trend_strength = close.rolling(order_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        
        # Pattern as order
        autocorr = returns.rolling(order_period).apply(
            lambda x: x.autocorr() if len(x) > 1 else 0
        )
        pattern_order = abs(autocorr)
        
        # Periodicity as order
        fft_strength = returns.rolling(order_period).apply(
            lambda x: abs(np.fft.fft(x)[1]) if len(x) > 1 else 0
        )
        periodicity = fft_strength / (fft_strength.rolling(chaos_period).max() + 1e-10)
        
        order_score = (
            0.4 * trend_strength +
            0.3 * pattern_order +
            0.3 * periodicity
        )
        
        # 3. Chaos-Order Transition
        transition_score = order_score - chaos_score
        transition_velocity = transition_score.diff(transition_period)
        
        # 4. Primordial Score
        primordial_score = (
            0.4 * order_score +
            0.3 * (1 - chaos_score) +
            0.3 * np.tanh(transition_velocity * 10)
        )
        
        result = pd.DataFrame(index=data.index)
        result['primordial_score'] = primordial_score
        result['chaos_score'] = chaos_score
        result['order_score'] = order_score
        result['transition_score'] = transition_score
        result['entropy'] = entropy_normalized
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['primordial_score'] > 0.6) &
            (indicator['order_score'] > 0.6) &
            (indicator['chaos_score'] < 0.4)
        )
        
        tp_pips = params.get('tp_pips', 150)
        sl_pips = params.get('sl_pips', 60)
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
        signal_strength = indicator['primordial_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on chaos return"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['primordial_score'] > 0.6) &
            (indicator['order_score'] > 0.6) &
            (indicator['chaos_score'] < 0.4)
        )
        
        exits = (
            (indicator['primordial_score'] < 0.2) |
            (indicator['chaos_score'] > 0.7)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['primordial_score'] < 0.2)] = 'order_breakdown'
        exit_reason[exits & (indicator['chaos_score'] > 0.7)] = 'chaos_return'
        
        signal_strength = indicator['primordial_score'].clip(0, 1)
        
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
        features['primordial_score'] = indicator['primordial_score']
        features['chaos_score'] = indicator['chaos_score']
        features['order_score'] = indicator['order_score']
        features['transition_score'] = indicator['transition_score']
        features['entropy'] = indicator['entropy']
        features['chaos_momentum'] = indicator['chaos_score'].diff(5)
        features['order_trend'] = indicator['order_score'].rolling(10).mean()
        features['transition_velocity'] = indicator['transition_score'].diff(5)
        features['entropy_stability'] = indicator['entropy'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'chaos_period': [55, 75, 89, 100, 125],
            'order_period': [34, 40, 55, 75, 100],
            'transition_period': [21, 30, 34, 40, 50],
            'tp_pips': [100, 125, 150, 200, 250],
            'sl_pips': [40, 50, 60, 75, 100]
        }
