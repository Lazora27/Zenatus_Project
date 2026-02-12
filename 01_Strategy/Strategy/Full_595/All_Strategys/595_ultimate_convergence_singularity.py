"""
595 - Ultimate Convergence Singularity
Ultimate Master Indicator: The ultimate singularity where all converges
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class UltimateConvergenceSingularity:
    """
    Ultimate Convergence Singularity - Final convergence point
    
    Features:
    - Singularity detection
    - Total convergence
    - Ultimate alignment
    - Singularity strength
    - Convergence quality
    """
    
    def __init__(self):
        self.name = "Ultimate Convergence Singularity"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate ultimate singularity score"""
        
        # Parameters
        singularity_period = params.get('singularity_period', 144)
        convergence_period = params.get('convergence_period', 89)
        alignment_period = params.get('alignment_period', 55)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Singularity Detection
        # Detect convergence of all forces
        
        # Price convergence
        ma_fast = close.rolling(21).mean()
        ma_medium = close.rolling(55).mean()
        ma_slow = close.rolling(144).mean()
        
        price_convergence = 1 - (
            abs(ma_fast - ma_medium) + abs(ma_medium - ma_slow)
        ) / (2 * close)
        
        # Indicator convergence
        rsi = self._calculate_rsi(close, alignment_period)
        momentum = returns.rolling(alignment_period).mean() / (returns.rolling(alignment_period).std() + 1e-10)
        
        rsi_signal = (rsi - 50) / 50
        momentum_signal = np.tanh(momentum)
        
        indicator_convergence = 1 - abs(rsi_signal - momentum_signal) / 2
        
        # Volume convergence
        volume_ma = volume.rolling(convergence_period).mean()
        volume_convergence = 1 / (1 + abs(volume - volume_ma) / volume_ma)
        
        singularity_detection = (
            0.4 * price_convergence +
            0.35 * indicator_convergence +
            0.25 * volume_convergence
        )
        
        # 2. Total Convergence
        # All dimensions converging
        
        # Temporal convergence (all timeframes agree)
        tf_short = returns.rolling(13).mean()
        tf_medium = returns.rolling(55).mean()
        tf_long = returns.rolling(144).mean()
        
        temporal_agreement = (
            (np.sign(tf_short) == np.sign(tf_medium)).astype(float) +
            (np.sign(tf_medium) == np.sign(tf_long)).astype(float) +
            (np.sign(tf_short) == np.sign(tf_long)).astype(float)
        ) / 3
        
        # Dimensional convergence
        price_dim = (close - close.rolling(convergence_period).min()) / (
            close.rolling(convergence_period).max() - close.rolling(convergence_period).min() + 1e-10
        )
        volume_dim = volume / volume.rolling(convergence_period).max()
        volatility_dim = returns.rolling(alignment_period).std() / returns.rolling(singularity_period).std()
        
        dimensional_convergence = 1 - np.std([price_dim, volume_dim, volatility_dim], axis=0)
        
        total_convergence = (temporal_agreement + dimensional_convergence) / 2
        
        # 3. Ultimate Alignment
        # Perfect alignment of all elements
        
        # Directional alignment
        price_direction = np.sign(close - close.shift(alignment_period))
        volume_direction = np.sign(volume - volume.shift(alignment_period))
        momentum_direction = np.sign(returns.rolling(alignment_period).mean())
        
        directional_alignment = (
            (price_direction == momentum_direction).astype(float) +
            (volume_direction == momentum_direction).astype(float) +
            (price_direction == volume_direction).astype(float)
        ) / 3
        
        # Phase alignment
        price_phase = np.arctan2(returns.rolling(alignment_period).std(),
                                returns.rolling(alignment_period).mean())
        volume_phase = np.arctan2(volume.pct_change().rolling(alignment_period).std(),
                                 volume.pct_change().rolling(alignment_period).mean())
        
        phase_alignment = 1 - abs(price_phase - volume_phase) / np.pi
        
        ultimate_alignment = (directional_alignment + phase_alignment) / 2
        
        # 4. Singularity Strength
        # How strong is the singularity
        
        convergence_magnitude = (
            singularity_detection * total_convergence * ultimate_alignment
        )
        
        # Persistence of singularity
        singularity_persistence = convergence_magnitude.rolling(convergence_period).mean()
        
        singularity_strength = (convergence_magnitude + singularity_persistence) / 2
        
        # 5. Convergence Quality
        # Quality of the convergence
        
        # Stability
        convergence_stability = 1 / (1 + singularity_detection.rolling(convergence_period).std())
        
        # Completeness
        components = [singularity_detection, total_convergence, ultimate_alignment]
        component_variance = np.std(components, axis=0)
        convergence_completeness = 1 / (1 + component_variance)
        
        convergence_quality = (convergence_stability + convergence_completeness) / 2
        
        # 6. Ultimate Singularity
        ultimate_singularity = (
            0.30 * singularity_detection +
            0.25 * total_convergence +
            0.25 * ultimate_alignment +
            0.15 * singularity_strength +
            0.05 * convergence_quality
        )
        
        # 7. Singularity State
        singularity_state = pd.Series(0, index=data.index)
        singularity_state[(ultimate_singularity > 0.9) & (convergence_quality > 0.9)] = 5  # Perfect singularity
        singularity_state[(ultimate_singularity > 0.8) & (ultimate_singularity <= 0.9)] = 4  # Strong
        singularity_state[(ultimate_singularity > 0.6) & (ultimate_singularity <= 0.8)] = 3  # Moderate
        singularity_state[(ultimate_singularity > 0.4) & (ultimate_singularity <= 0.6)] = 2  # Weak
        singularity_state[(ultimate_singularity > 0.2) & (ultimate_singularity <= 0.4)] = 1  # Forming
        singularity_state[ultimate_singularity <= 0.2] = 0  # Divergent
        
        result = pd.DataFrame(index=data.index)
        result['ultimate_singularity'] = ultimate_singularity
        result['singularity_detection'] = singularity_detection
        result['total_convergence'] = total_convergence
        result['ultimate_alignment'] = ultimate_alignment
        result['singularity_strength'] = singularity_strength
        result['convergence_quality'] = convergence_quality
        result['singularity_state'] = singularity_state
        
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
        
        entries = (
            (indicator['ultimate_singularity'] > 0.85) &
            (indicator['convergence_quality'] > 0.85) &
            (indicator['singularity_state'] >= 4)
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
        signal_strength = indicator['ultimate_singularity'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on singularity breakdown"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['ultimate_singularity'] > 0.85) &
            (indicator['convergence_quality'] > 0.85) &
            (indicator['singularity_state'] >= 4)
        )
        
        exits = (
            (indicator['ultimate_singularity'] < 0.3) |
            (indicator['singularity_state'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['ultimate_singularity'] < 0.3)] = 'singularity_collapse'
        exit_reason[exits & (indicator['singularity_state'] <= 1)] = 'divergence_onset'
        
        signal_strength = indicator['ultimate_singularity'].clip(0, 1)
        
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
        features['ultimate_singularity'] = indicator['ultimate_singularity']
        features['singularity_detection'] = indicator['singularity_detection']
        features['total_convergence'] = indicator['total_convergence']
        features['ultimate_alignment'] = indicator['ultimate_alignment']
        features['singularity_strength'] = indicator['singularity_strength']
        features['convergence_quality'] = indicator['convergence_quality']
        features['singularity_state'] = indicator['singularity_state']
        features['singularity_momentum'] = indicator['ultimate_singularity'].diff(5)
        features['convergence_trend'] = indicator['total_convergence'].rolling(10).mean()
        features['quality_stability'] = indicator['convergence_quality'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'singularity_period': [89, 100, 125, 144, 200],
            'convergence_period': [55, 75, 89, 100, 125],
            'alignment_period': [34, 40, 55, 75, 100],
            'tp_pips': [300, 400, 500, 600, 750],
            'sl_pips': [125, 150, 200, 250, 300]
        }
