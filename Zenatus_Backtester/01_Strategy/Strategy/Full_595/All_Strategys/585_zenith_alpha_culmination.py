"""
585 - Zenith Alpha Culmination
Ultimate Master Indicator: Reaches the zenith of alpha generation
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class ZenithAlphaCulmination:
    """
    Zenith Alpha Culmination - Peak alpha achievement
    
    Features:
    - Peak alpha detection
    - Culmination point identification
    - Zenith quality measurement
    - Alpha maximization
    - Ultimate achievement scoring
    """
    
    def __init__(self):
        self.name = "Zenith Alpha Culmination"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate zenith alpha score"""
        
        # Parameters
        zenith_period = params.get('zenith_period', 100)
        culmination_period = params.get('culmination_period', 60)
        peak_period = params.get('peak_period', 40)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Peak Alpha Detection
        # Multiple alpha sources
        momentum_alpha = returns.rolling(peak_period).mean() / (returns.rolling(peak_period).std() + 1e-10)
        trend_alpha = close.rolling(culmination_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        ) / close
        volume_alpha = volume / volume.rolling(zenith_period).mean()
        
        combined_alpha = (
            0.4 * np.tanh(momentum_alpha) +
            0.35 * np.tanh(trend_alpha * 100) +
            0.25 * np.tanh(volume_alpha - 1)
        )
        
        # Peak detection
        is_peak = (combined_alpha == combined_alpha.rolling(peak_period).max()).astype(float)
        peak_alpha = combined_alpha * is_peak
        
        # 2. Culmination Point
        # Identify culmination of all forces
        price_at_high = (close == close.rolling(culmination_period).max()).astype(float)
        volume_at_high = (volume == volume.rolling(culmination_period).max()).astype(float)
        momentum_at_high = (momentum_alpha == momentum_alpha.rolling(culmination_period).max()).astype(float)
        
        culmination_point = (price_at_high + volume_at_high + momentum_at_high) / 3
        
        # 3. Zenith Quality
        # Quality of the peak
        alpha_purity = abs(combined_alpha) / (abs(combined_alpha).rolling(zenith_period).max() + 1e-10)
        
        # Consistency leading to peak
        pre_peak_consistency = combined_alpha.rolling(peak_period).apply(
            lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        zenith_quality = (alpha_purity + pre_peak_consistency) / 2
        
        # 4. Zenith Alpha
        zenith_alpha = (
            0.40 * combined_alpha +
            0.30 * peak_alpha +
            0.20 * culmination_point +
            0.10 * zenith_quality
        )
        
        # 5. Achievement Level
        achievement_level = pd.Series(0, index=data.index)
        achievement_level[(zenith_alpha > 0.8) & (zenith_quality > 0.8)] = 5  # Ultimate zenith
        achievement_level[(zenith_alpha > 0.6) & (zenith_alpha <= 0.8)] = 4  # Peak
        achievement_level[(zenith_alpha > 0.4) & (zenith_alpha <= 0.6)] = 3  # High
        achievement_level[(zenith_alpha > 0.2) & (zenith_alpha <= 0.4)] = 2  # Moderate
        achievement_level[(zenith_alpha > 0) & (zenith_alpha <= 0.2)] = 1  # Low
        achievement_level[zenith_alpha <= 0] = 0  # None
        
        result = pd.DataFrame(index=data.index)
        result['zenith_alpha'] = zenith_alpha
        result['combined_alpha'] = combined_alpha
        result['peak_alpha'] = peak_alpha
        result['culmination_point'] = culmination_point
        result['zenith_quality'] = zenith_quality
        result['achievement_level'] = achievement_level
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['zenith_alpha'] > 0.7) &
            (indicator['zenith_quality'] > 0.7) &
            (indicator['achievement_level'] >= 4)
        )
        
        tp_pips = params.get('tp_pips', 250)
        sl_pips = params.get('sl_pips', 100)
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
        signal_strength = indicator['zenith_alpha'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on zenith decline"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['zenith_alpha'] > 0.7) &
            (indicator['zenith_quality'] > 0.7) &
            (indicator['achievement_level'] >= 4)
        )
        
        exits = (
            (indicator['zenith_alpha'] < 0.2) |
            (indicator['achievement_level'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['zenith_alpha'] < 0.2)] = 'zenith_decline'
        exit_reason[exits & (indicator['achievement_level'] <= 1)] = 'achievement_loss'
        
        signal_strength = indicator['zenith_alpha'].clip(-1, 1)
        
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
        features['zenith_alpha'] = indicator['zenith_alpha']
        features['combined_alpha'] = indicator['combined_alpha']
        features['peak_alpha'] = indicator['peak_alpha']
        features['culmination_point'] = indicator['culmination_point']
        features['zenith_quality'] = indicator['zenith_quality']
        features['achievement_level'] = indicator['achievement_level']
        features['spiritual_momentum'] = indicator['zenith_alpha'].diff()  # Calculated momentum
        features['alpha_momentum'] = indicator['zenith_alpha'].diff(5)
        features['quality_trend'] = indicator['zenith_quality'].rolling(10).mean()
        features['peak_frequency'] = indicator['peak_alpha'].rolling(20).sum()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'zenith_period': [75, 100, 125, 150, 200],
            'culmination_period': [50, 60, 75, 100, 125],
            'peak_period': [30, 40, 50, 60, 75],
            'tp_pips': [150, 200, 250, 300, 400],
            'sl_pips': [60, 75, 100, 125, 150]
        }
