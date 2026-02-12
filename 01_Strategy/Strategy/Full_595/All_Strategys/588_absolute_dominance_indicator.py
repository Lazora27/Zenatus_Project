"""
588 - Absolute Dominance Indicator
Ultimate Master Indicator: Measures absolute market dominance and control
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class AbsoluteDominanceIndicator:
    """
    Absolute Dominance Indicator - Market dominance measurement
    
    Features:
    - Dominance strength
    - Control measurement
    - Power concentration
    - Authority scoring
    - Supremacy detection
    """
    
    def __init__(self):
        self.name = "Absolute Dominance Indicator"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate absolute dominance score"""
        
        # Parameters
        dominance_period = params.get('dominance_period', 100)
        power_period = params.get('power_period', 60)
        control_period = params.get('control_period', 40)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Dominance Strength
        # Price dominance (relative position)
        price_percentile = close.rolling(dominance_period).apply(
            lambda x: (x[-1] >= x).sum() / len(x) if len(x) > 0 else 0.5
        )
        price_dominance = (price_percentile - 0.5) * 2
        
        # Trend dominance
        trend_consistency = close.rolling(power_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        trend_direction = np.sign(close.rolling(power_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        ))
        trend_dominance = trend_consistency * trend_direction
        
        # Momentum dominance
        momentum = returns.rolling(control_period).mean()
        momentum_strength = abs(momentum) / (returns.rolling(control_period).std() + 1e-10)
        momentum_dominance = np.tanh(momentum_strength) * np.sign(momentum)
        
        dominance_strength = (
            0.4 * price_dominance +
            0.35 * trend_dominance +
            0.25 * momentum_dominance
        )
        
        # 2. Control Measurement
        # Market control (price action efficiency)
        price_control = abs(close - close.shift(1)) / ((high - low) + 1e-10)
        price_control = price_control.rolling(control_period).mean()
        
        # Volume control
        volume_consistency = 1 / (1 + volume.rolling(control_period).std() / (volume.rolling(control_period).mean() + 1e-10))
        
        # Volatility control
        volatility = returns.rolling(control_period).std()
        volatility_control = 1 / (1 + volatility / (volatility.rolling(dominance_period).mean() + 1e-10))
        
        control_measurement = (
            0.4 * price_control +
            0.3 * volume_consistency +
            0.3 * volatility_control
        )
        
        # 3. Power Concentration
        # How concentrated is the power
        price_range = close.rolling(power_period).max() - close.rolling(power_period).min()
        current_position = (close - close.rolling(power_period).min()) / (price_range + 1e-10)
        
        # Power at extremes (high concentration)
        power_at_extremes = abs(current_position - 0.5) * 2
        
        # Volume concentration
        volume_concentration = volume / volume.rolling(power_period).mean()
        volume_concentration = np.tanh(volume_concentration - 1)
        
        power_concentration = (
            0.6 * power_at_extremes +
            0.4 * volume_concentration
        )
        
        # 4. Authority Scoring
        # Market authority (ability to move market)
        price_impact = abs(returns) * volume
        price_impact_normalized = price_impact / price_impact.rolling(dominance_period).max()
        
        # Directional authority
        directional_consistency = abs(np.sign(returns).rolling(power_period).sum()) / power_period
        
        # Leadership (leading vs following)
        price_change = close.pct_change(control_period)
        volume_change = volume.pct_change(control_period)
        leadership = price_change.rolling(power_period).corr(volume_change.shift(1))
        
        authority_score = (
            0.4 * price_impact_normalized +
            0.35 * directional_consistency +
            0.25 * abs(leadership)
        )
        
        # 5. Supremacy Detection
        # Detect supreme dominance
        at_high = (close == close.rolling(dominance_period).max()).astype(float)
        sustained_high = at_high.rolling(control_period).sum() / control_period
        
        volume_supremacy = (volume == volume.rolling(dominance_period).max()).astype(float)
        
        supremacy_score = (
            0.6 * sustained_high +
            0.4 * volume_supremacy.rolling(control_period).mean()
        )
        
        # 6. Absolute Dominance
        absolute_dominance = (
            0.30 * dominance_strength +
            0.25 * control_measurement +
            0.20 * power_concentration +
            0.15 * authority_score +
            0.10 * supremacy_score
        )
        
        # 7. Dominance Level
        dominance_level = pd.Series(0, index=data.index)
        dominance_level[(absolute_dominance > 0.8) & (supremacy_score > 0.7)] = 5  # Absolute
        dominance_level[(absolute_dominance > 0.6) & (absolute_dominance <= 0.8)] = 4  # Supreme
        dominance_level[(absolute_dominance > 0.4) & (absolute_dominance <= 0.6)] = 3  # Strong
        dominance_level[(absolute_dominance > 0.2) & (absolute_dominance <= 0.4)] = 2  # Moderate
        dominance_level[(absolute_dominance > 0) & (absolute_dominance <= 0.2)] = 1  # Weak
        dominance_level[absolute_dominance <= 0] = 0  # None
        
        result = pd.DataFrame(index=data.index)
        result['absolute_dominance'] = absolute_dominance
        result['dominance_strength'] = dominance_strength
        result['control_measurement'] = control_measurement
        result['power_concentration'] = power_concentration
        result['authority_score'] = authority_score
        result['supremacy_score'] = supremacy_score
        result['dominance_level'] = dominance_level
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['absolute_dominance'] > 0.75) &
            (indicator['authority_score'] > 0.7) &
            (indicator['dominance_level'] >= 4)
        )
        
        tp_pips = params.get('tp_pips', 300)
        sl_pips = params.get('sl_pips', 125)
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
        signal_strength = indicator['absolute_dominance'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on dominance loss"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['absolute_dominance'] > 0.75) &
            (indicator['authority_score'] > 0.7) &
            (indicator['dominance_level'] >= 4)
        )
        
        exits = (
            (indicator['absolute_dominance'] < 0.2) |
            (indicator['dominance_level'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['absolute_dominance'] < 0.2)] = 'dominance_loss'
        exit_reason[exits & (indicator['dominance_level'] <= 1)] = 'power_collapse'
        
        signal_strength = indicator['absolute_dominance'].clip(-1, 1)
        
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
        features['absolute_dominance'] = indicator['absolute_dominance']
        features['dominance_strength'] = indicator['dominance_strength']
        features['control_measurement'] = indicator['control_measurement']
        features['power_concentration'] = indicator['power_concentration']
        features['authority_score'] = indicator['authority_score']
        features['supremacy_score'] = indicator['supremacy_score']
        features['dominance_level'] = indicator['dominance_level']
        features['dominance_momentum'] = indicator['absolute_dominance'].diff(5)
        features['control_trend'] = indicator['control_measurement'].rolling(10).mean()
        features['authority_stability'] = indicator['authority_score'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'dominance_period': [75, 100, 125, 150, 200],
            'power_period': [50, 60, 75, 100, 125],
            'control_period': [30, 40, 50, 60, 75],
            'tp_pips': [200, 250, 300, 400, 500],
            'sl_pips': [75, 100, 125, 150, 200]
        }
