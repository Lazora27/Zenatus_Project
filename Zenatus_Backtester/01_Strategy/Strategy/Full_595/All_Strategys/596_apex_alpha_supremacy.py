"""
596 - Apex Alpha Supremacy
Grand Finale Indicator: Supreme apex of all alpha generation
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class ApexAlphaSupremacy:
    """
    Apex Alpha Supremacy - The highest alpha achievement
    
    Features:
    - Apex detection
    - Alpha supremacy
    - Peak performance
    - Supreme quality
    - Ultimate achievement
    """
    
    def __init__(self):
        self.name = "Apex Alpha Supremacy"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate apex alpha supremacy score"""
        
        # Parameters
        apex_period = params.get('apex_period', 144)
        supremacy_period = params.get('supremacy_period', 89)
        peak_period = params.get('peak_period', 55)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Apex Detection
        # Detect apex points
        is_apex = (close == close.rolling(apex_period).max()).astype(float)
        apex_frequency = is_apex.rolling(supremacy_period).mean()
        
        # Distance to apex
        distance_to_apex = (close.rolling(apex_period).max() - close) / close
        apex_proximity = 1 / (1 + distance_to_apex)
        
        apex_detection = (apex_frequency + apex_proximity) / 2
        
        # 2. Alpha Supremacy
        # Multiple alpha sources
        momentum_alpha = returns.rolling(peak_period).mean() / (returns.rolling(peak_period).std() + 1e-10)
        trend_alpha = close.rolling(supremacy_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        ) / close
        volume_alpha = np.tanh((volume / volume.rolling(apex_period).mean()) - 1)
        
        combined_alpha = (
            0.4 * np.tanh(momentum_alpha) +
            0.35 * np.tanh(trend_alpha * 100) +
            0.25 * volume_alpha
        )
        
        # Alpha dominance
        alpha_percentile = combined_alpha.rolling(apex_period).apply(
            lambda x: (x[-1] >= x).sum() / len(x) if len(x) > 0 else 0.5
        )
        alpha_supremacy = alpha_percentile
        
        # 3. Peak Performance
        # Performance at peak
        sharpe = returns.rolling(supremacy_period).mean() / (returns.rolling(supremacy_period).std() + 1e-10)
        sharpe_normalized = np.tanh(sharpe)
        
        win_rate = (returns > 0).rolling(supremacy_period).mean()
        
        profit_factor = returns.where(returns > 0, 0).rolling(supremacy_period).sum() / (
            abs(returns.where(returns < 0, 0).rolling(supremacy_period).sum()) + 1e-10
        )
        profit_factor_normalized = np.tanh(profit_factor - 1.5)
        
        peak_performance = (
            0.4 * sharpe_normalized +
            0.35 * win_rate +
            0.25 * profit_factor_normalized
        )
        
        # 4. Supreme Quality
        quality_consistency = 1 / (1 + combined_alpha.rolling(supremacy_period).std())
        quality_strength = abs(combined_alpha)
        quality_persistence = combined_alpha.rolling(peak_period).apply(
            lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        supreme_quality = (
            0.4 * quality_consistency +
            0.3 * quality_strength +
            0.3 * quality_persistence
        )
        
        # 5. Apex Alpha Supremacy
        apex_alpha_supremacy = (
            0.30 * apex_detection +
            0.30 * alpha_supremacy +
            0.25 * peak_performance +
            0.15 * supreme_quality
        )
        
        # 6. Supremacy Level
        supremacy_level = pd.Series(0, index=data.index)
        supremacy_level[(apex_alpha_supremacy > 0.9) & (supreme_quality > 0.85)] = 6  # Absolute apex
        supremacy_level[(apex_alpha_supremacy > 0.8) & (apex_alpha_supremacy <= 0.9)] = 5  # Supreme
        supremacy_level[(apex_alpha_supremacy > 0.6) & (apex_alpha_supremacy <= 0.8)] = 4  # Dominant
        supremacy_level[(apex_alpha_supremacy > 0.4) & (apex_alpha_supremacy <= 0.6)] = 3  # Strong
        supremacy_level[(apex_alpha_supremacy > 0.2) & (apex_alpha_supremacy <= 0.4)] = 2  # Moderate
        supremacy_level[(apex_alpha_supremacy > 0) & (apex_alpha_supremacy <= 0.2)] = 1  # Weak
        supremacy_level[apex_alpha_supremacy <= 0] = 0  # None
        
        result = pd.DataFrame(index=data.index)
        result['apex_alpha_supremacy'] = apex_alpha_supremacy
        result['apex_detection'] = apex_detection
        result['alpha_supremacy'] = alpha_supremacy
        result['peak_performance'] = peak_performance
        result['supreme_quality'] = supreme_quality
        result['supremacy_level'] = supremacy_level
        result['combined_alpha'] = combined_alpha
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['apex_alpha_supremacy'] > 0.85) &
            (indicator['supreme_quality'] > 0.8) &
            (indicator['supremacy_level'] >= 5)
        )
        
        tp_pips = params.get('tp_pips', 500)
        sl_pips = params.get('sl_pips', 200)
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
        signal_strength = indicator['apex_alpha_supremacy'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on supremacy loss"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['apex_alpha_supremacy'] > 0.85) &
            (indicator['supreme_quality'] > 0.8) &
            (indicator['supremacy_level'] >= 5)
        )
        
        exits = (
            (indicator['apex_alpha_supremacy'] < 0.2) |
            (indicator['supremacy_level'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['apex_alpha_supremacy'] < 0.2)] = 'supremacy_loss'
        exit_reason[exits & (indicator['supremacy_level'] <= 1)] = 'apex_decline'
        
        signal_strength = indicator['apex_alpha_supremacy'].clip(0, 1)
        
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
        features['apex_alpha_supremacy'] = indicator['apex_alpha_supremacy']
        features['apex_detection'] = indicator['apex_detection']
        features['alpha_supremacy'] = indicator['alpha_supremacy']
        features['peak_performance'] = indicator['peak_performance']
        features['supreme_quality'] = indicator['supreme_quality']
        features['supremacy_level'] = indicator['supremacy_level']
        features['combined_alpha'] = indicator['combined_alpha']
        features['supremacy_momentum'] = indicator['apex_alpha_supremacy'].diff(5)
        features['quality_trend'] = indicator['supreme_quality'].rolling(10).mean()
        features['performance_stability'] = indicator['peak_performance'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'apex_period': [89, 100, 125, 144, 200],
            'supremacy_period': [55, 75, 89, 100, 125],
            'peak_period': [34, 40, 55, 75, 100],
            'tp_pips': [300, 400, 500, 600, 750],
            'sl_pips': [125, 150, 200, 250, 300]
        }
