"""
571 - Singularity Convergence Detector
Ultimate Master Indicator: Detects market singularity points where all forces converge
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class SingularityConvergenceDetector:
    """
    Singularity Convergence Detector - Identifies critical convergence points
    
    Features:
    - Multi-force convergence detection
    - Singularity strength measurement
    - Critical point identification
    - Convergence momentum tracking
    - Divergence risk assessment
    """
    
    def __init__(self):
        self.name = "Singularity Convergence Detector"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate singularity convergence score"""
        
        # Parameters
        singularity_period = params.get('singularity_period', 50)
        convergence_period = params.get('convergence_period', 30)
        critical_threshold = params.get('critical_threshold', 0.8)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Multi-Force Convergence Detection
        returns = close.pct_change()
        
        # Price force
        price_ma_fast = close.rolling(10).mean()
        price_ma_slow = close.rolling(singularity_period).mean()
        price_force = (price_ma_fast - price_ma_slow) / price_ma_slow
        
        # Momentum force
        momentum = returns.rolling(convergence_period).mean() / (returns.rolling(convergence_period).std() + 1e-10)
        momentum_force = np.tanh(momentum)
        
        # Volume force
        volume_ma = volume.rolling(singularity_period).mean()
        volume_force = np.tanh((volume / volume_ma) - 1)
        
        # Volatility force
        volatility = returns.rolling(convergence_period).std()
        volatility_ma = volatility.rolling(singularity_period).mean()
        volatility_force = -np.tanh((volatility / volatility_ma) - 1)  # Low vol = positive
        
        # Trend force
        trend_strength = close.rolling(convergence_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        trend_direction = np.sign(close.rolling(convergence_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        ))
        trend_force = trend_strength * trend_direction
        
        # 2. Singularity Strength Measurement
        forces = [price_force, momentum_force, volume_force, volatility_force, trend_force]
        
        # Force alignment (all pointing same direction)
        force_signs = pd.DataFrame({f'force_{i}': np.sign(f) for i, f in enumerate(forces)})
        force_alignment = force_signs.sum(axis=1) / len(forces)
        
        # Force magnitude
        force_magnitude = pd.Series(0.0, index=data.index)
        for force in forces:
            force_magnitude += force ** 2
        force_magnitude = np.sqrt(force_magnitude / len(forces))
        
        singularity_strength = abs(force_alignment) * force_magnitude
        
        # 3. Critical Point Identification
        # Detect when forces are converging (getting closer)
        force_variance = pd.Series(0.0, index=data.index)
        mean_force = sum(forces) / len(forces)
        for force in forces:
            force_variance += (force - mean_force) ** 2
        force_variance = np.sqrt(force_variance / len(forces))
        
        # Low variance = high convergence
        convergence_score = 1 / (1 + force_variance)
        
        # Critical point when convergence is high and strength is high
        critical_point = (convergence_score > critical_threshold) & (singularity_strength > 0.6)
        
        # 4. Convergence Momentum Tracking
        convergence_velocity = convergence_score.diff(5)
        convergence_acceleration = convergence_velocity.diff(3)
        
        convergence_momentum = (
            0.5 * np.tanh(convergence_velocity * 10) +
            0.5 * np.tanh(convergence_acceleration * 100)
        )
        
        # 5. Divergence Risk Assessment
        # Measure how quickly forces could diverge
        force_volatility = force_variance.rolling(convergence_period).std()
        divergence_risk = force_volatility / (force_variance + 1e-10)
        divergence_risk = np.tanh(divergence_risk)
        
        # Historical divergence frequency
        divergence_events = (force_variance.diff() > 0).astype(int)
        divergence_frequency = divergence_events.rolling(singularity_period).mean()
        
        divergence_risk_score = (divergence_risk + divergence_frequency) / 2
        
        # 6. Singularity Score
        singularity_score = (
            0.35 * singularity_strength +
            0.30 * convergence_score +
            0.20 * convergence_momentum +
            0.15 * (1 - divergence_risk_score)
        )
        
        # 7. Singularity State
        singularity_state = pd.Series(0, index=data.index)
        singularity_state[critical_point & (force_alignment > 0.8)] = 3  # Critical bullish
        singularity_state[(singularity_score > 0.6) & (force_alignment > 0.5)] = 2  # Strong convergence
        singularity_state[(singularity_score > 0.4) & (singularity_score <= 0.6)] = 1  # Moderate
        singularity_state[singularity_score <= 0.4] = 0  # Weak
        
        # 8. Time to Singularity (estimated)
        convergence_rate = convergence_velocity.rolling(10).mean()
        time_to_singularity = (critical_threshold - convergence_score) / (abs(convergence_rate) + 1e-10)
        time_to_singularity = time_to_singularity.clip(0, 100)
        
        result = pd.DataFrame(index=data.index)
        result['singularity_score'] = singularity_score
        result['singularity_strength'] = singularity_strength
        result['convergence_score'] = convergence_score
        result['force_alignment'] = force_alignment
        result['convergence_momentum'] = convergence_momentum
        result['divergence_risk_score'] = divergence_risk_score
        result['singularity_state'] = singularity_state
        result['time_to_singularity'] = time_to_singularity
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Critical singularity point with low divergence risk
        entries = (
            (indicator['singularity_score'] > 0.7) &
            (indicator['convergence_score'] > 0.7) &
            (indicator['divergence_risk_score'] < 0.4) &
            (indicator['singularity_state'] >= 2)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 125)
        sl_pips = params.get('sl_pips', 50)
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
        
        signal_strength = indicator['singularity_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on divergence onset"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Critical singularity
        entries = (
            (indicator['singularity_score'] > 0.7) &
            (indicator['convergence_score'] > 0.7) &
            (indicator['divergence_risk_score'] < 0.4) &
            (indicator['singularity_state'] >= 2)
        )
        
        # Exit: Divergence or convergence breakdown
        exits = (
            (indicator['singularity_score'] < 0.3) |
            (indicator['divergence_risk_score'] > 0.7) |
            (indicator['convergence_score'] < 0.3)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['singularity_score'] < 0.3)] = 'singularity_collapse'
        exit_reason[exits & (indicator['divergence_risk_score'] > 0.7)] = 'divergence_onset'
        exit_reason[exits & (indicator['convergence_score'] < 0.3)] = 'convergence_breakdown'
        
        signal_strength = indicator['singularity_score'].clip(0, 1)
        
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
        features['singularity_score'] = indicator['singularity_score']
        features['singularity_strength'] = indicator['singularity_strength']
        features['convergence_score'] = indicator['convergence_score']
        features['force_alignment'] = indicator['force_alignment']
        features['convergence_momentum'] = indicator['convergence_momentum']
        features['divergence_risk_score'] = indicator['divergence_risk_score']
        features['singularity_state'] = indicator['singularity_state']
        features['time_to_singularity'] = indicator['time_to_singularity']
        
        # Additional features
        features['singularity_velocity'] = indicator['singularity_score'].diff(5)
        features['convergence_trend'] = indicator['convergence_score'].rolling(10).mean()
        features['risk_volatility'] = indicator['divergence_risk_score'].rolling(15).std()
        features['alignment_stability'] = indicator['force_alignment'].rolling(20).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'singularity_period': [40, 50, 60, 75, 100],
            'convergence_period': [20, 25, 30, 40, 50],
            'critical_threshold': [0.7, 0.75, 0.8, 0.85, 0.9],
            'tp_pips': [75, 100, 125, 150, 200],
            'sl_pips': [30, 40, 50, 60, 75]
        }
