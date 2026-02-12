"""
561 - Cognitive Market Intelligence
Ultimate Master Indicator: Simulates cognitive decision-making processes with multi-layer intelligence
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class CognitiveMarketIntelligence:
    """
    Cognitive Market Intelligence - Simulates human-like market cognition
    
    Combines:
    - Pattern recognition layers
    - Memory-based learning
    - Attention mechanisms
    - Decision confidence scoring
    """
    
    def __init__(self):
        self.name = "Cognitive Market Intelligence"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate cognitive intelligence score"""
        
        # Parameters
        memory_period = params.get('memory_period', 50)
        attention_period = params.get('attention_period', 20)
        pattern_period = params.get('pattern_period', 10)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Pattern Recognition Layer
        returns = close.pct_change()
        pattern_score = returns.rolling(pattern_period).apply(
            lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1] if len(x) > 1 else 0
        )
        
        # 2. Memory Layer (Long-term context)
        memory_mean = close.rolling(memory_period).mean()
        memory_std = close.rolling(memory_period).std()
        memory_score = (close - memory_mean) / (memory_std + 1e-10)
        
        # 3. Attention Mechanism (Focus on recent important events)
        volatility = returns.rolling(attention_period).std()
        volume_attention = volume / volume.rolling(attention_period).mean()
        attention_score = volatility * volume_attention
        attention_score = attention_score / (attention_score.rolling(attention_period).max() + 1e-10)
        
        # 4. Decision Confidence
        price_momentum = close.rolling(attention_period).apply(
            lambda x: (x[-1] - x[0]) / x[0] if x[0] != 0 else 0
        )
        volume_momentum = volume.rolling(attention_period).mean() / volume.rolling(memory_period).mean()
        confidence = np.tanh(price_momentum * volume_momentum)
        
        # 5. Cognitive Integration Score
        cognitive_score = (
            0.3 * pattern_score +
            0.25 * np.tanh(memory_score) +
            0.25 * attention_score +
            0.2 * confidence
        )
        
        # 6. Cognitive State Classification
        cognitive_state = pd.Series(0, index=data.index)
        cognitive_state[cognitive_score > 0.5] = 2  # Strong bullish cognition
        cognitive_state[(cognitive_score > 0) & (cognitive_score <= 0.5)] = 1  # Weak bullish
        cognitive_state[(cognitive_score < 0) & (cognitive_score >= -0.5)] = -1  # Weak bearish
        cognitive_state[cognitive_score < -0.5] = -2  # Strong bearish cognition
        
        result = pd.DataFrame(index=data.index)
        result['cognitive_score'] = cognitive_score
        result['pattern_score'] = pattern_score
        result['memory_score'] = np.tanh(memory_score)
        result['attention_score'] = attention_score
        result['confidence'] = confidence
        result['cognitive_state'] = cognitive_state
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong cognitive bullish state with high confidence
        entries = (
            (indicator['cognitive_score'] > 0.3) &
            (indicator['confidence'] > 0.2) &
            (indicator['cognitive_state'] >= 1)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 60)
        sl_pips = params.get('sl_pips', 30)
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
        
        signal_strength = indicator['cognitive_score'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on cognitive state change"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong cognitive bullish state
        entries = (
            (indicator['cognitive_score'] > 0.3) &
            (indicator['confidence'] > 0.2) &
            (indicator['cognitive_state'] >= 1)
        )
        
        # Exit: Cognitive state reversal or confidence drop
        exits = (
            (indicator['cognitive_score'] < 0) |
            (indicator['confidence'] < -0.1) |
            (indicator['cognitive_state'] <= -1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['cognitive_score'] < 0)] = 'cognitive_reversal'
        exit_reason[exits & (indicator['confidence'] < -0.1)] = 'confidence_drop'
        exit_reason[exits & (indicator['cognitive_state'] <= -1)] = 'state_change'
        
        signal_strength = indicator['cognitive_score'].clip(-1, 1)
        
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
        features['cognitive_score'] = indicator['cognitive_score']
        features['pattern_score'] = indicator['pattern_score']
        features['memory_score'] = indicator['memory_score']
        features['attention_score'] = indicator['attention_score']
        features['confidence'] = indicator['confidence']
        features['cognitive_state'] = indicator['cognitive_state']
        
        # Additional features
        features['cognitive_momentum'] = indicator['cognitive_score'].diff(5)
        features['cognitive_acceleration'] = features['cognitive_momentum'].diff(3)
        features['confidence_trend'] = indicator['confidence'].rolling(10).mean()
        features['attention_volatility'] = indicator['attention_score'].rolling(10).std()
        features['pattern_consistency'] = indicator['pattern_score'].rolling(15).std()
        features['memory_deviation'] = indicator['memory_score'].rolling(20).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'memory_period': [30, 40, 50, 60, 75],
            'attention_period': [10, 15, 20, 25, 30],
            'pattern_period': [5, 8, 10, 13, 15],
            'tp_pips': [40, 50, 60, 75, 100],
            'sl_pips': [20, 25, 30, 40, 50]
        }
