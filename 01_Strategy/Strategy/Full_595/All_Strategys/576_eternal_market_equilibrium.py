"""
576 - Eternal Market Equilibrium
Ultimate Master Indicator: Identifies eternal equilibrium states in market dynamics
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class EternalMarketEquilibrium:
    """
    Eternal Market Equilibrium - Perfect balance point detection
    
    Features:
    - Equilibrium state identification
    - Balance measurement
    - Stability assessment
    - Disruption detection
    - Restoration tracking
    """
    
    def __init__(self):
        self.name = "Eternal Market Equilibrium"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate eternal equilibrium score"""
        
        # Parameters
        equilibrium_period = params.get('equilibrium_period', 100)
        balance_period = params.get('balance_period', 50)
        stability_period = params.get('stability_period', 30)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Equilibrium State Identification
        returns = close.pct_change()
        
        # Price equilibrium (mean reversion point)
        price_mean = close.rolling(equilibrium_period).mean()
        price_deviation = (close - price_mean) / price_mean
        price_equilibrium = 1 / (1 + abs(price_deviation))
        
        # Volume equilibrium
        volume_mean = volume.rolling(equilibrium_period).mean()
        volume_deviation = (volume - volume_mean) / volume_mean
        volume_equilibrium = 1 / (1 + abs(volume_deviation))
        
        # Volatility equilibrium
        volatility = returns.rolling(balance_period).std()
        volatility_mean = volatility.rolling(equilibrium_period).mean()
        volatility_deviation = (volatility - volatility_mean) / volatility_mean
        volatility_equilibrium = 1 / (1 + abs(volatility_deviation))
        
        # Combined equilibrium state
        equilibrium_state = (
            0.4 * price_equilibrium +
            0.3 * volume_equilibrium +
            0.3 * volatility_equilibrium
        )
        
        # 2. Balance Measurement
        # Supply-demand balance (simulated via price-volume relationship)
        price_change = close.pct_change(balance_period)
        volume_change = volume.pct_change(balance_period)
        
        supply_demand_balance = 1 - abs(price_change.rolling(balance_period).corr(volume_change))
        
        # Buyer-seller balance (via price position in range)
        price_position = (close - low.rolling(balance_period).min()) / (
            high.rolling(balance_period).max() - low.rolling(balance_period).min() + 1e-10
        )
        balance_score = 1 - abs(price_position - 0.5) * 2
        
        # Momentum balance
        momentum_up = (returns > 0).rolling(balance_period).sum()
        momentum_down = (returns < 0).rolling(balance_period).sum()
        momentum_balance = 1 - abs(momentum_up - momentum_down) / balance_period
        
        balance_measurement = (
            0.4 * supply_demand_balance +
            0.3 * balance_score +
            0.3 * momentum_balance
        )
        
        # 3. Stability Assessment
        # Price stability
        price_stability = 1 / (1 + returns.rolling(stability_period).std())
        
        # Trend stability (low directional changes)
        trend_direction = np.sign(returns)
        trend_changes = (trend_direction != trend_direction.shift()).astype(int)
        trend_stability = 1 - trend_changes.rolling(stability_period).mean()
        
        # Range stability
        range_size = (high - low) / close
        range_stability = 1 / (1 + range_size.rolling(stability_period).std())
        
        stability_assessment = (
            0.4 * price_stability +
            0.3 * trend_stability +
            0.3 * range_stability
        )
        
        # 4. Disruption Detection
        # Sudden price disruptions
        price_shock = abs(returns) > returns.rolling(equilibrium_period).quantile(0.95)
        disruption_frequency = price_shock.astype(int).rolling(balance_period).sum() / balance_period
        
        # Volume disruptions
        volume_shock = volume > volume.rolling(equilibrium_period).quantile(0.95)
        volume_disruption = volume_shock.astype(int).rolling(balance_period).sum() / balance_period
        
        # Volatility disruptions
        volatility_shock = volatility > volatility.rolling(equilibrium_period).quantile(0.95)
        volatility_disruption = volatility_shock.astype(int).rolling(balance_period).sum() / balance_period
        
        disruption_level = (
            0.4 * disruption_frequency +
            0.3 * volume_disruption +
            0.3 * volatility_disruption
        )
        
        # 5. Restoration Tracking
        # How quickly market returns to equilibrium after disruption
        deviation_from_equilibrium = abs(price_deviation)
        
        # Restoration speed
        restoration_speed = -deviation_from_equilibrium.diff(stability_period)
        restoration_speed = np.tanh(restoration_speed * 10)
        
        # Time since last equilibrium
        at_equilibrium = (equilibrium_state > 0.7).astype(int)
        time_since_equilibrium = pd.Series(0, index=data.index)
        
        counter = 0
        for i in range(len(data)):
            if at_equilibrium.iloc[i]:
                counter = 0
            else:
                counter += 1
            time_since_equilibrium.iloc[i] = counter
        
        restoration_urgency = time_since_equilibrium / equilibrium_period
        restoration_urgency = restoration_urgency.clip(0, 1)
        
        restoration_tracking = (
            0.6 * (restoration_speed + 1) / 2 +  # Normalize to 0-1
            0.4 * (1 - restoration_urgency)
        )
        
        # 6. Eternal Equilibrium Score
        eternal_equilibrium = (
            0.30 * equilibrium_state +
            0.25 * balance_measurement +
            0.20 * stability_assessment +
            0.15 * (1 - disruption_level) +
            0.10 * restoration_tracking
        )
        
        # 7. Equilibrium Quality
        component_variance = pd.Series(0.0, index=data.index)
        components = [equilibrium_state, balance_measurement, stability_assessment,
                     1 - disruption_level, restoration_tracking]
        for comp in components:
            component_variance += (comp - eternal_equilibrium) ** 2
        component_variance = np.sqrt(component_variance / len(components))
        
        equilibrium_quality = 1 / (1 + component_variance)
        
        # 8. Market Phase
        market_phase = pd.Series(0, index=data.index)
        market_phase[(eternal_equilibrium > 0.8) & (disruption_level < 0.2)] = 3  # Perfect equilibrium
        market_phase[(eternal_equilibrium > 0.6) & (eternal_equilibrium <= 0.8)] = 2  # Stable
        market_phase[(eternal_equilibrium > 0.4) & (eternal_equilibrium <= 0.6)] = 1  # Transitioning
        market_phase[eternal_equilibrium <= 0.4] = 0  # Disrupted
        
        result = pd.DataFrame(index=data.index)
        result['eternal_equilibrium'] = eternal_equilibrium
        result['equilibrium_state'] = equilibrium_state
        result['balance_measurement'] = balance_measurement
        result['stability_assessment'] = stability_assessment
        result['disruption_level'] = disruption_level
        result['restoration_tracking'] = restoration_tracking
        result['equilibrium_quality'] = equilibrium_quality
        result['market_phase'] = market_phase
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Perfect equilibrium with low disruption
        entries = (
            (indicator['eternal_equilibrium'] > 0.75) &
            (indicator['equilibrium_quality'] > 0.7) &
            (indicator['disruption_level'] < 0.3) &
            (indicator['market_phase'] >= 2)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 150)
        sl_pips = params.get('sl_pips', 60)
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
        
        signal_strength = indicator['eternal_equilibrium'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on equilibrium disruption"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Perfect equilibrium
        entries = (
            (indicator['eternal_equilibrium'] > 0.75) &
            (indicator['equilibrium_quality'] > 0.7) &
            (indicator['disruption_level'] < 0.3) &
            (indicator['market_phase'] >= 2)
        )
        
        # Exit: Equilibrium disruption
        exits = (
            (indicator['eternal_equilibrium'] < 0.3) |
            (indicator['disruption_level'] > 0.7) |
            (indicator['market_phase'] <= 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['eternal_equilibrium'] < 0.3)] = 'equilibrium_loss'
        exit_reason[exits & (indicator['disruption_level'] > 0.7)] = 'major_disruption'
        exit_reason[exits & (indicator['market_phase'] <= 0)] = 'phase_breakdown'
        
        signal_strength = indicator['eternal_equilibrium'].clip(0, 1)
        
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
        features['eternal_equilibrium'] = indicator['eternal_equilibrium']
        features['equilibrium_state'] = indicator['equilibrium_state']
        features['balance_measurement'] = indicator['balance_measurement']
        features['stability_assessment'] = indicator['stability_assessment']
        features['disruption_level'] = indicator['disruption_level']
        features['restoration_tracking'] = indicator['restoration_tracking']
        features['equilibrium_quality'] = indicator['equilibrium_quality']
        features['market_phase'] = indicator['market_phase']
        
        # Additional features
        features['equilibrium_momentum'] = indicator['eternal_equilibrium'].diff(5)
        features['disruption_trend'] = indicator['disruption_level'].rolling(10).mean()
        features['stability_volatility'] = indicator['stability_assessment'].rolling(15).std()
        features['restoration_speed'] = indicator['restoration_tracking'].diff(5)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'equilibrium_period': [75, 100, 125, 150, 200],
            'balance_period': [40, 50, 60, 75, 100],
            'stability_period': [20, 25, 30, 40, 50],
            'tp_pips': [100, 125, 150, 175, 200],
            'sl_pips': [40, 50, 60, 75, 100]
        }
