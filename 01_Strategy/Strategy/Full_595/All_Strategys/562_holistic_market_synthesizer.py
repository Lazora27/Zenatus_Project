"""
562 - Holistic Market Synthesizer
Ultimate Master Indicator: Synthesizes all market dimensions into unified intelligence
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class HolisticMarketSynthesizer:
    """
    Holistic Market Synthesizer - Unified multi-dimensional market analysis
    
    Synthesizes:
    - Price action dimension
    - Volume dimension
    - Volatility dimension
    - Momentum dimension
    - Microstructure dimension
    """
    
    def __init__(self):
        self.name = "Holistic Market Synthesizer"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate holistic synthesis score"""
        
        # Parameters
        synthesis_period = params.get('synthesis_period', 30)
        fast_period = params.get('fast_period', 10)
        slow_period = params.get('slow_period', 50)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Price Action Dimension
        returns = close.pct_change()
        price_trend = close.rolling(synthesis_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        )
        price_strength = (close - close.rolling(synthesis_period).min()) / (
            close.rolling(synthesis_period).max() - close.rolling(synthesis_period).min() + 1e-10
        )
        price_dimension = np.tanh(price_trend * 100) * price_strength
        
        # 2. Volume Dimension
        volume_ma = volume.rolling(synthesis_period).mean()
        volume_ratio = volume / (volume_ma + 1e-10)
        volume_trend = volume.rolling(fast_period).mean() / volume.rolling(slow_period).mean()
        volume_dimension = np.tanh(volume_ratio - 1) * np.tanh(volume_trend - 1)
        
        # 3. Volatility Dimension
        volatility = returns.rolling(synthesis_period).std()
        volatility_ma = volatility.rolling(slow_period).mean()
        volatility_ratio = volatility / (volatility_ma + 1e-10)
        atr = (high - low).rolling(synthesis_period).mean()
        atr_normalized = atr / close
        volatility_dimension = np.tanh(volatility_ratio - 1) * (1 - atr_normalized.clip(0, 1))
        
        # 4. Momentum Dimension
        roc = close.pct_change(fast_period)
        rsi = self._calculate_rsi(close, synthesis_period)
        momentum_strength = (roc * 100).rolling(fast_period).mean()
        momentum_dimension = np.tanh(momentum_strength) * ((rsi - 50) / 50)
        
        # 5. Microstructure Dimension
        hl_range = (high - low) / close
        co_range = abs(close - close.shift(1)) / close
        efficiency = co_range / (hl_range + 1e-10)
        tick_direction = np.sign(close.diff())
        tick_imbalance = tick_direction.rolling(synthesis_period).sum() / synthesis_period
        microstructure_dimension = efficiency.rolling(fast_period).mean() * tick_imbalance
        
        # 6. Holistic Synthesis
        synthesis_score = (
            0.25 * price_dimension +
            0.20 * volume_dimension +
            0.20 * volatility_dimension +
            0.20 * momentum_dimension +
            0.15 * microstructure_dimension
        )
        
        # 7. Synthesis Confidence
        dimension_agreement = pd.Series(0.0, index=data.index)
        dimensions = [price_dimension, volume_dimension, volatility_dimension, 
                     momentum_dimension, microstructure_dimension]
        for dim in dimensions:
            dimension_agreement += (np.sign(dim) == np.sign(synthesis_score)).astype(float)
        dimension_agreement = dimension_agreement / len(dimensions)
        
        # 8. Synthesis Quality
        synthesis_volatility = synthesis_score.rolling(synthesis_period).std()
        synthesis_quality = 1 / (1 + synthesis_volatility)
        
        result = pd.DataFrame(index=data.index)
        result['synthesis_score'] = synthesis_score
        result['price_dimension'] = price_dimension
        result['volume_dimension'] = volume_dimension
        result['volatility_dimension'] = volatility_dimension
        result['momentum_dimension'] = momentum_dimension
        result['microstructure_dimension'] = microstructure_dimension
        result['dimension_agreement'] = dimension_agreement
        result['synthesis_quality'] = synthesis_quality
        
        return result
    
    def _calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong synthesis with high agreement and quality
        entries = (
            (indicator['synthesis_score'] > 0.3) &
            (indicator['dimension_agreement'] > 0.6) &
            (indicator['synthesis_quality'] > 0.5)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 75)
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
        
        signal_strength = indicator['synthesis_score'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on synthesis deterioration"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong synthesis
        entries = (
            (indicator['synthesis_score'] > 0.3) &
            (indicator['dimension_agreement'] > 0.6) &
            (indicator['synthesis_quality'] > 0.5)
        )
        
        # Exit: Synthesis reversal or quality drop
        exits = (
            (indicator['synthesis_score'] < 0) |
            (indicator['dimension_agreement'] < 0.4) |
            (indicator['synthesis_quality'] < 0.3)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['synthesis_score'] < 0)] = 'synthesis_reversal'
        exit_reason[exits & (indicator['dimension_agreement'] < 0.4)] = 'dimension_disagreement'
        exit_reason[exits & (indicator['synthesis_quality'] < 0.3)] = 'quality_deterioration'
        
        signal_strength = indicator['synthesis_score'].clip(-1, 1)
        
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
        features['synthesis_score'] = indicator['synthesis_score']
        features['price_dimension'] = indicator['price_dimension']
        features['volume_dimension'] = indicator['volume_dimension']
        features['volatility_dimension'] = indicator['volatility_dimension']
        features['momentum_dimension'] = indicator['momentum_dimension']
        features['microstructure_dimension'] = indicator['microstructure_dimension']
        features['dimension_agreement'] = indicator['dimension_agreement']
        features['synthesis_quality'] = indicator['synthesis_quality']
        
        # Additional features
        features['synthesis_momentum'] = indicator['synthesis_score'].diff(5)
        features['synthesis_acceleration'] = features['synthesis_momentum'].diff(3)
        features['agreement_trend'] = indicator['dimension_agreement'].rolling(10).mean()
        features['quality_stability'] = indicator['synthesis_quality'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'synthesis_period': [20, 25, 30, 40, 50],
            'fast_period': [5, 8, 10, 13, 15],
            'slow_period': [40, 50, 60, 75, 100],
            'tp_pips': [50, 60, 75, 100, 125],
            'sl_pips': [20, 25, 30, 40, 50]
        }
