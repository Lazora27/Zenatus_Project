"""
587 - Master Synthesis Nexus
Ultimate Master Indicator: Central nexus for all market synthesis
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class MasterSynthesisNexus:
    """
    Master Synthesis Nexus - Central synthesis point
    
    Features:
    - Nexus point identification
    - Synthesis convergence
    - Master integration
    - Nexus power measurement
    - Central force detection
    """
    
    def __init__(self):
        self.name = "Master Synthesis Nexus"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate master nexus score"""
        
        # Parameters
        nexus_period = params.get('nexus_period', 100)
        synthesis_period = params.get('synthesis_period', 60)
        convergence_period = params.get('convergence_period', 40)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Nexus Point Identification
        # Central price level
        nexus_price = close.rolling(nexus_period).median()
        distance_to_nexus = abs(close - nexus_price) / nexus_price
        nexus_proximity = 1 / (1 + distance_to_nexus)
        
        # Central volume level
        nexus_volume = volume.rolling(nexus_period).median()
        volume_at_nexus = 1 / (1 + abs(volume - nexus_volume) / nexus_volume)
        
        # Nexus strength
        nexus_strength = (nexus_proximity + volume_at_nexus) / 2
        
        # 2. Synthesis Convergence
        # Multiple indicators converging
        ma_fast = close.rolling(20).mean()
        ma_medium = close.rolling(50).mean()
        ma_slow = close.rolling(100).mean()
        
        ma_convergence = 1 - (
            abs(ma_fast - ma_medium) + abs(ma_medium - ma_slow)
        ) / (2 * close)
        
        # Oscillator convergence
        rsi = self._calculate_rsi(close, convergence_period)
        momentum = returns.rolling(convergence_period).mean() / (returns.rolling(convergence_period).std() + 1e-10)
        
        rsi_signal = (rsi - 50) / 50
        momentum_signal = np.tanh(momentum)
        
        oscillator_convergence = 1 - abs(rsi_signal - momentum_signal) / 2
        
        synthesis_convergence = (ma_convergence + oscillator_convergence) / 2
        
        # 3. Master Integration
        # Integrate all market aspects
        price_component = (close - close.rolling(synthesis_period).min()) / (
            close.rolling(synthesis_period).max() - close.rolling(synthesis_period).min() + 1e-10
        )
        price_component = (price_component - 0.5) * 2
        
        volume_component = volume / volume.rolling(synthesis_period).mean()
        volume_component = np.tanh(volume_component - 1)
        
        volatility_component = returns.rolling(convergence_period).std()
        volatility_component = volatility_component / volatility_component.rolling(nexus_period).mean()
        volatility_component = -np.tanh(volatility_component - 1)
        
        trend_component = close.rolling(synthesis_period).apply(
            lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1] if len(x) > 1 else 0
        )
        
        master_integration = (
            0.3 * price_component +
            0.25 * volume_component +
            0.25 * volatility_component +
            0.20 * trend_component
        )
        
        # 4. Nexus Power
        nexus_power = (
            0.35 * nexus_strength +
            0.35 * synthesis_convergence +
            0.30 * master_integration
        )
        
        # 5. Central Force
        force_magnitude = abs(nexus_power)
        force_direction = np.sign(master_integration)
        central_force = force_magnitude * force_direction
        
        # 6. Nexus Quality
        nexus_stability = 1 / (1 + nexus_power.rolling(synthesis_period).std())
        convergence_quality = synthesis_convergence
        
        nexus_quality = (nexus_stability + convergence_quality) / 2
        
        result = pd.DataFrame(index=data.index)
        result['nexus_power'] = nexus_power
        result['nexus_strength'] = nexus_strength
        result['synthesis_convergence'] = synthesis_convergence
        result['master_integration'] = master_integration
        result['central_force'] = central_force
        result['nexus_quality'] = nexus_quality
        
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
            (indicator['nexus_power'] > 0.7) &
            (indicator['nexus_quality'] > 0.7) &
            (indicator['central_force'] > 0.5)
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
        signal_strength = indicator['nexus_power'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on nexus breakdown"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['nexus_power'] > 0.7) &
            (indicator['nexus_quality'] > 0.7) &
            (indicator['central_force'] > 0.5)
        )
        
        exits = (
            (indicator['nexus_power'] < 0.2) |
            (indicator['nexus_quality'] < 0.3)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['nexus_power'] < 0.2)] = 'nexus_breakdown'
        exit_reason[exits & (indicator['nexus_quality'] < 0.3)] = 'quality_loss'
        
        signal_strength = indicator['nexus_power'].clip(-1, 1)
        
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
        features['nexus_power'] = indicator['nexus_power']
        features['nexus_strength'] = indicator['nexus_strength']
        features['synthesis_convergence'] = indicator['synthesis_convergence']
        features['master_integration'] = indicator['master_integration']
        features['central_force'] = indicator['central_force']
        features['nexus_quality'] = indicator['nexus_quality']
        features['universe_trend'] = indicator['master_synthesis'].rolling(10).mean()  # Calculated trend
        features['universe_momentum'] = indicator['master_synthesis'].diff()  # Calculated momentum
        features['nexus_momentum'] = indicator['nexus_power'].diff(5)
        features['quality_trend'] = indicator['nexus_quality'].rolling(10).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'nexus_period': [75, 100, 125, 144, 200],
            'synthesis_period': [50, 60, 75, 89, 100],
            'convergence_period': [30, 40, 50, 55, 75],
            'tp_pips': [150, 200, 250, 300, 400],
            'sl_pips': [60, 75, 100, 125, 150]
        }
