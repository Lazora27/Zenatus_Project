"""
575 - Omnipotent Market Force
Ultimate Master Indicator: Measures the omnipotent force driving market movements
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class OmnipotentMarketForce:
    """
    Omnipotent Market Force - Ultimate force measurement
    
    Features:
    - Force magnitude calculation
    - Force direction identification
    - Force persistence measurement
    - Force acceleration tracking
    - Force dominance assessment
    """
    
    def __init__(self):
        self.name = "Omnipotent Market Force"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate omnipotent force score"""
        
        # Parameters
        force_period = params.get('force_period', 60)
        power_period = params.get('power_period', 40)
        momentum_period = params.get('momentum_period', 20)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Force Magnitude Calculation
        returns = close.pct_change()
        
        # Price force (momentum)
        price_momentum = returns.rolling(momentum_period).mean()
        price_force_magnitude = abs(price_momentum) / (returns.rolling(momentum_period).std() + 1e-10)
        price_force = np.tanh(price_force_magnitude) * np.sign(price_momentum)
        
        # Volume force (buying/selling pressure)
        volume_change = volume.pct_change()
        volume_momentum = volume_change.rolling(momentum_period).mean()
        volume_force_magnitude = volume / volume.rolling(force_period).mean()
        volume_force = np.tanh(volume_force_magnitude - 1) * np.sign(price_momentum)
        
        # Volatility force (energy)
        volatility = returns.rolling(momentum_period).std()
        volatility_mean = volatility.rolling(force_period).mean()
        volatility_force = volatility / (volatility_mean + 1e-10)
        volatility_force = np.tanh(volatility_force - 1)
        
        # Trend force (directional strength)
        trend_slope = close.rolling(power_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        )
        trend_force = np.tanh(trend_slope * 100)
        
        # Combined force magnitude
        force_magnitude = np.sqrt(
            price_force**2 + volume_force**2 + volatility_force**2 + trend_force**2
        ) / 2  # Normalize
        
        # 2. Force Direction Identification
        # Primary direction
        primary_direction = np.sign(price_force + trend_force)
        
        # Direction confidence
        direction_components = [price_force, volume_force, trend_force]
        direction_agreement = pd.Series(0.0, index=data.index)
        for comp in direction_components:
            direction_agreement += (np.sign(comp) == primary_direction).astype(float)
        direction_agreement = direction_agreement / len(direction_components)
        
        # Force direction (with confidence)
        force_direction = primary_direction * direction_agreement
        
        # 3. Force Persistence Measurement
        # How long has force been in same direction
        direction_changes = (primary_direction != primary_direction.shift()).astype(int)
        persistence_counter = pd.Series(0, index=data.index)
        
        counter = 0
        for i in range(len(data)):
            if direction_changes.iloc[i]:
                counter = 0
            else:
                counter += 1
            persistence_counter.iloc[i] = counter
        
        force_persistence = persistence_counter / force_period
        force_persistence = force_persistence.clip(0, 1)
        
        # Force stability (low variance = high persistence)
        force_stability = 1 / (1 + force_magnitude.rolling(power_period).std())
        
        persistence_score = (force_persistence + force_stability) / 2
        
        # 4. Force Acceleration Tracking
        # First derivative (velocity)
        force_velocity = force_magnitude.diff(5)
        
        # Second derivative (acceleration)
        force_acceleration = force_velocity.diff(3)
        
        # Jerk (third derivative - rate of acceleration change)
        force_jerk = force_acceleration.diff(2)
        
        # Combined acceleration score
        acceleration_score = (
            0.5 * np.tanh(force_velocity * 10) +
            0.3 * np.tanh(force_acceleration * 100) +
            0.2 * np.tanh(force_jerk * 1000)
        )
        
        # 5. Force Dominance Assessment
        # Measure how dominant this force is
        
        # Relative strength (vs historical)
        force_percentile = force_magnitude.rolling(force_period).apply(
            lambda x: (x[-1] >= x).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        # Market control (how much of price action is explained)
        explained_variance = (force_magnitude * abs(returns)).rolling(power_period).sum() / (
            abs(returns).rolling(power_period).sum() + 1e-10
        )
        
        # Force concentration (focused vs dispersed)
        force_concentration = force_magnitude / (force_magnitude.rolling(power_period).mean() + 1e-10)
        force_concentration = np.tanh(force_concentration - 1)
        
        force_dominance = (
            0.4 * force_percentile +
            0.3 * explained_variance +
            0.3 * force_concentration
        )
        
        # 6. Omnipotent Force Score
        omnipotent_force = (
            0.30 * force_magnitude +
            0.25 * abs(force_direction) +
            0.20 * persistence_score +
            0.15 * acceleration_score +
            0.10 * force_dominance
        )
        
        # 7. Force Power Level
        force_power = pd.Series(0, index=data.index)
        force_power[(omnipotent_force > 0.8) & (force_dominance > 0.7)] = 5  # Omnipotent
        force_power[(omnipotent_force > 0.7) & (omnipotent_force <= 0.8)] = 4  # Dominant
        force_power[(omnipotent_force > 0.5) & (omnipotent_force <= 0.7)] = 3  # Strong
        force_power[(omnipotent_force > 0.3) & (omnipotent_force <= 0.5)] = 2  # Moderate
        force_power[(omnipotent_force > 0.1) & (omnipotent_force <= 0.3)] = 1  # Weak
        force_power[omnipotent_force <= 0.1] = 0  # Negligible
        
        # 8. Directional Force (force with direction)
        directional_force = omnipotent_force * force_direction
        
        result = pd.DataFrame(index=data.index)
        result['omnipotent_force'] = omnipotent_force
        result['force_magnitude'] = force_magnitude
        result['force_direction'] = force_direction
        result['persistence_score'] = persistence_score
        result['acceleration_score'] = acceleration_score
        result['force_dominance'] = force_dominance
        result['force_power'] = force_power
        result['directional_force'] = directional_force
        result['direction_agreement'] = direction_agreement
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Omnipotent force with clear direction
        entries = (
            (indicator['omnipotent_force'] > 0.75) &
            (indicator['directional_force'] > 0.6) &
            (indicator['force_dominance'] > 0.6) &
            (indicator['force_power'] >= 4)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 200)
        sl_pips = params.get('sl_pips', 75)
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
        
        signal_strength = indicator['omnipotent_force'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on force weakening"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Omnipotent force
        entries = (
            (indicator['omnipotent_force'] > 0.75) &
            (indicator['directional_force'] > 0.6) &
            (indicator['force_dominance'] > 0.6) &
            (indicator['force_power'] >= 4)
        )
        
        # Exit: Force weakening or reversal
        exits = (
            (indicator['omnipotent_force'] < 0.3) |
            (indicator['force_dominance'] < 0.3) |
            (indicator['force_power'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['omnipotent_force'] < 0.3)] = 'force_weakening'
        exit_reason[exits & (indicator['force_dominance'] < 0.3)] = 'dominance_loss'
        exit_reason[exits & (indicator['force_power'] <= 1)] = 'power_collapse'
        
        signal_strength = indicator['omnipotent_force'].clip(0, 1)
        
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
        features['omnipotent_force'] = indicator['omnipotent_force']
        features['force_magnitude'] = indicator['force_magnitude']
        features['force_direction'] = indicator['force_direction']
        features['persistence_score'] = indicator['persistence_score']
        features['acceleration_score'] = indicator['acceleration_score']
        features['force_dominance'] = indicator['force_dominance']
        features['force_power'] = indicator['force_power']
        features['directional_force'] = indicator['directional_force']
        features['direction_agreement'] = indicator['direction_agreement']
        
        # Additional features
        features['force_velocity'] = indicator['omnipotent_force'].diff(5)
        features['dominance_trend'] = indicator['force_dominance'].rolling(10).mean()
        features['persistence_stability'] = indicator['persistence_score'].rolling(15).std()
        features['power_consistency'] = indicator['force_power'].rolling(20).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'force_period': [50, 60, 75, 100, 125],
            'power_period': [30, 40, 50, 60, 75],
            'momentum_period': [15, 20, 25, 30, 40],
            'tp_pips': [125, 150, 200, 250, 300],
            'sl_pips': [50, 60, 75, 100, 125]
        }
