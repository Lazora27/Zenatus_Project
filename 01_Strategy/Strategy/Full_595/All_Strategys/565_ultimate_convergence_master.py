"""
565 - Ultimate Convergence Master
Ultimate Master Indicator: Master convergence of all analytical dimensions
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class UltimateConvergenceMaster:
    """
    Ultimate Convergence Master - Convergence of all market forces
    
    Integrates:
    - Technical convergence
    - Fundamental convergence
    - Sentiment convergence
    - Microstructure convergence
    - Temporal convergence
    """
    
    def __init__(self):
        self.name = "Ultimate Convergence Master"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate ultimate convergence score"""
        
        # Parameters
        convergence_period = params.get('convergence_period', 40)
        fast_period = params.get('fast_period', 10)
        slow_period = params.get('slow_period', 60)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Technical Convergence
        # Multiple moving average convergence
        ma_fast = close.rolling(fast_period).mean()
        ma_medium = close.rolling(convergence_period).mean()
        ma_slow = close.rolling(slow_period).mean()
        
        ma_convergence = (
            np.sign(close - ma_fast) +
            np.sign(ma_fast - ma_medium) +
            np.sign(ma_medium - ma_slow)
        ) / 3
        
        # Oscillator convergence
        returns = close.pct_change()
        rsi = self._calculate_rsi(close, convergence_period)
        rsi_signal = (rsi - 50) / 50
        
        momentum = returns.rolling(convergence_period).mean() / (returns.rolling(convergence_period).std() + 1e-10)
        momentum_signal = np.tanh(momentum)
        
        oscillator_convergence = (rsi_signal + momentum_signal) / 2
        
        technical_convergence = 0.6 * ma_convergence + 0.4 * oscillator_convergence
        
        # 2. Volume Convergence
        volume_ma_fast = volume.rolling(fast_period).mean()
        volume_ma_slow = volume.rolling(slow_period).mean()
        
        volume_trend = volume_ma_fast / (volume_ma_slow + 1e-10)
        volume_strength = volume / (volume.rolling(convergence_period).mean() + 1e-10)
        
        volume_convergence = np.tanh(volume_trend - 1) * np.tanh(volume_strength - 1)
        
        # 3. Volatility Convergence
        volatility = returns.rolling(convergence_period).std()
        volatility_ma = volatility.rolling(slow_period).mean()
        
        atr = (high - low).rolling(convergence_period).mean()
        atr_ma = atr.rolling(slow_period).mean()
        
        vol_convergence = (volatility - volatility_ma) / (volatility_ma + 1e-10)
        atr_convergence = (atr - atr_ma) / (atr_ma + 1e-10)
        
        volatility_convergence = np.tanh((vol_convergence + atr_convergence) / 2)
        
        # 4. Microstructure Convergence
        # Price efficiency
        hl_range = (high - low) / close
        co_range = abs(close - close.shift(1)) / close
        efficiency = co_range / (hl_range + 1e-10)
        efficiency_ma = efficiency.rolling(convergence_period).mean()
        
        # Tick analysis
        tick_direction = np.sign(close.diff())
        tick_imbalance = tick_direction.rolling(convergence_period).sum() / convergence_period
        tick_imbalance_ma = tick_imbalance.rolling(slow_period).mean()
        
        microstructure_convergence = (
            0.5 * (efficiency - efficiency_ma) +
            0.5 * (tick_imbalance - tick_imbalance_ma)
        )
        
        # 5. Temporal Convergence
        # Multi-timeframe alignment
        price_change_short = close.pct_change(fast_period)
        price_change_medium = close.pct_change(convergence_period)
        price_change_long = close.pct_change(slow_period)
        
        temporal_alignment = (
            np.sign(price_change_short) +
            np.sign(price_change_medium) +
            np.sign(price_change_long)
        ) / 3
        
        # Trend consistency
        trend_consistency = close.rolling(convergence_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        
        temporal_convergence = 0.6 * temporal_alignment + 0.4 * trend_consistency
        
        # 6. Ultimate Convergence Score
        convergence_score = (
            0.30 * technical_convergence +
            0.20 * volume_convergence +
            0.15 * volatility_convergence +
            0.15 * microstructure_convergence +
            0.20 * temporal_convergence
        )
        
        # 7. Convergence Strength
        components = [
            technical_convergence,
            volume_convergence,
            volatility_convergence,
            microstructure_convergence,
            temporal_convergence
        ]
        
        convergence_agreement = pd.Series(0.0, index=data.index)
        for comp in components:
            convergence_agreement += (np.sign(comp) == np.sign(convergence_score)).astype(float)
        convergence_agreement = convergence_agreement / len(components)
        
        # 8. Convergence Quality
        convergence_volatility = convergence_score.rolling(convergence_period).std()
        convergence_quality = 1 / (1 + convergence_volatility)
        
        # 9. Convergence Momentum
        convergence_momentum = convergence_score.diff(5)
        convergence_acceleration = convergence_momentum.diff(3)
        
        result = pd.DataFrame(index=data.index)
        result['convergence_score'] = convergence_score
        result['technical_convergence'] = technical_convergence
        result['volume_convergence'] = volume_convergence
        result['volatility_convergence'] = volatility_convergence
        result['microstructure_convergence'] = microstructure_convergence
        result['temporal_convergence'] = temporal_convergence
        result['convergence_agreement'] = convergence_agreement
        result['convergence_quality'] = convergence_quality
        result['convergence_momentum'] = convergence_momentum
        result['convergence_acceleration'] = convergence_acceleration
        
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
        
        # Entry: Strong convergence with high agreement and quality
        entries = (
            (indicator['convergence_score'] > 0.4) &
            (indicator['convergence_agreement'] > 0.7) &
            (indicator['convergence_quality'] > 0.6) &
            (indicator['convergence_momentum'] > 0)
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
        
        signal_strength = indicator['convergence_score'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on convergence breakdown"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong convergence
        entries = (
            (indicator['convergence_score'] > 0.4) &
            (indicator['convergence_agreement'] > 0.7) &
            (indicator['convergence_quality'] > 0.6) &
            (indicator['convergence_momentum'] > 0)
        )
        
        # Exit: Convergence breakdown
        exits = (
            (indicator['convergence_score'] < 0) |
            (indicator['convergence_agreement'] < 0.4) |
            (indicator['convergence_momentum'] < -0.1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['convergence_score'] < 0)] = 'convergence_reversal'
        exit_reason[exits & (indicator['convergence_agreement'] < 0.4)] = 'divergence_detected'
        exit_reason[exits & (indicator['convergence_momentum'] < -0.1)] = 'momentum_breakdown'
        
        signal_strength = indicator['convergence_score'].clip(-1, 1)
        
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
        features['convergence_score'] = indicator['convergence_score']
        features['technical_convergence'] = indicator['technical_convergence']
        features['volume_convergence'] = indicator['volume_convergence']
        features['volatility_convergence'] = indicator['volatility_convergence']
        features['microstructure_convergence'] = indicator['microstructure_convergence']
        features['temporal_convergence'] = indicator['temporal_convergence']
        features['convergence_agreement'] = indicator['convergence_agreement']
        features['convergence_quality'] = indicator['convergence_quality']
        features['convergence_momentum'] = indicator['convergence_momentum']
        features['convergence_acceleration'] = indicator['convergence_acceleration']
        
        # Additional features
        features['agreement_stability'] = indicator['convergence_agreement'].rolling(15).std()
        features['quality_trend'] = indicator['convergence_quality'].rolling(20).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'convergence_period': [30, 40, 50, 60, 75],
            'fast_period': [5, 8, 10, 13, 15],
            'slow_period': [50, 60, 75, 100, 125],
            'tp_pips': [60, 75, 100, 125, 150],
            'sl_pips': [25, 30, 40, 50, 60]
        }
