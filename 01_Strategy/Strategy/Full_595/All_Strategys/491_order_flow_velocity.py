"""
491_order_flow_velocity.py
===========================
Indicator: Order Flow Velocity
Category: Market Microstructure / Flow Dynamics
Complexity: Advanced

Description:
-----------
Measures the speed and acceleration of order flow changes. Identifies rapid shifts
in buying/selling pressure that precede price movements. Critical for detecting
momentum shifts and institutional activity bursts.

Key Features:
- Flow velocity (rate of change)
- Flow acceleration
- Momentum bursts detection
- Velocity divergence

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_OrderFlowVelocity:
    """
    Order Flow Velocity Indicator
    
    Measures speed and acceleration of order flow.
    """
    
    def __init__(self):
        self.name = "Order Flow Velocity"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Order Flow Velocity metrics
        
        Parameters:
        - velocity_period: Period for velocity calculation (default: 8)
        - acceleration_period: Period for acceleration (default: 5)
        - burst_threshold: Threshold for burst detection (default: 2.0)
        """
        velocity_period = params.get('velocity_period', 8)
        acceleration_period = params.get('acceleration_period', 5)
        burst_threshold = params.get('burst_threshold', 2.0)
        
        # 1. Order Flow Proxy (signed volume)
        price_change = data['close'].diff()
        order_flow = data['volume'] * np.sign(price_change)
        
        # 2. Flow Velocity (rate of change in flow)
        flow_velocity = order_flow.diff(velocity_period) / velocity_period
        
        # 3. Flow Acceleration (rate of change in velocity)
        flow_acceleration = flow_velocity.diff(acceleration_period) / acceleration_period
        
        # 4. Velocity Magnitude (absolute speed)
        velocity_magnitude = abs(flow_velocity)
        
        # 5. Normalized Velocity (z-score)
        velocity_mean = flow_velocity.rolling(window=velocity_period * 3).mean()
        velocity_std = flow_velocity.rolling(window=velocity_period * 3).std()
        velocity_normalized = (flow_velocity - velocity_mean) / (velocity_std + 1e-10)
        
        # 6. Momentum Burst Detection (extreme velocity)
        momentum_burst = (abs(velocity_normalized) > burst_threshold).astype(int)
        
        # 7. Velocity Direction (positive = buying, negative = selling)
        velocity_direction = np.sign(flow_velocity)
        
        # 8. Acceleration Direction
        acceleration_direction = np.sign(flow_acceleration)
        
        # 9. Velocity-Price Divergence
        price_velocity = data['close'].pct_change(velocity_period)
        velocity_divergence = (
            (velocity_direction != np.sign(price_velocity)) &
            (abs(velocity_normalized) > 1.0)
        ).astype(int)
        
        # 10. Flow Momentum Score (velocity * acceleration alignment)
        momentum_score = velocity_normalized * (acceleration_direction == velocity_direction).astype(int)
        
        # 11. Velocity Persistence (consecutive periods of same direction)
        velocity_persistence = pd.Series(0, index=data.index)
        current_direction = 0
        persistence_count = 0
        
        for i in range(len(data)):
            direction = velocity_direction.iloc[i]
            if direction == current_direction and direction != 0:
                persistence_count += 1
            else:
                current_direction = direction
                persistence_count = 1
            velocity_persistence.iloc[i] = persistence_count
        
        # 12. Velocity Exhaustion (high velocity with decelerating acceleration)
        velocity_exhaustion = (
            (velocity_magnitude > velocity_magnitude.rolling(window=velocity_period).quantile(0.8)) &
            (flow_acceleration * velocity_direction < 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'order_flow': order_flow,
            'flow_velocity': flow_velocity,
            'flow_acceleration': flow_acceleration,
            'velocity_magnitude': velocity_magnitude,
            'velocity_normalized': velocity_normalized,
            'momentum_burst': momentum_burst,
            'velocity_direction': velocity_direction,
            'acceleration_direction': acceleration_direction,
            'velocity_divergence': velocity_divergence,
            'momentum_score': momentum_score,
            'velocity_persistence': velocity_persistence,
            'velocity_exhaustion': velocity_exhaustion
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When momentum burst detected with positive velocity
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Momentum burst + positive velocity + acceleration aligned
        entries = (
            (result['momentum_burst'] == 1) &
            (result['velocity_direction'] > 0) &
            (result['acceleration_direction'] > 0) &
            (result['velocity_persistence'] > 2) &
            (result['velocity_exhaustion'] == 0)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
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
        
        # Signal strength based on velocity magnitude
        signal_strength = (result['velocity_magnitude'] / result['velocity_magnitude'].rolling(window=50).mean()).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategy - Indicator-based
        
        Entry: Momentum burst detected
        Exit: When velocity exhaustion or direction reversal
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['momentum_burst'] == 1) &
            (result['velocity_direction'] > 0) &
            (result['acceleration_direction'] > 0) &
            (result['velocity_persistence'] > 2) &
            (result['velocity_exhaustion'] == 0)
        )
        
        # Exit: Velocity exhaustion or direction reversal or divergence
        exits = (
            (result['velocity_exhaustion'] == 1) |
            (result['velocity_direction'] < 0) |
            (result['velocity_divergence'] == 1) |
            (result['acceleration_direction'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['velocity_exhaustion'] == 1] = 'velocity_exhaustion'
        exit_reason[result['velocity_direction'] < 0] = 'direction_reversal'
        exit_reason[result['velocity_divergence'] == 1] = 'velocity_divergence'
        
        signal_strength = (result['velocity_magnitude'] / result['velocity_magnitude'].rolling(window=50).mean()).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 12 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'ofv_order_flow': result['order_flow'],
            'ofv_velocity': result['flow_velocity'],
            'ofv_acceleration': result['flow_acceleration'],
            'ofv_magnitude': result['velocity_magnitude'],
            'ofv_normalized': result['velocity_normalized'],
            'ofv_momentum_burst': result['momentum_burst'],
            'ofv_velocity_direction': result['velocity_direction'],
            'ofv_acceleration_direction': result['acceleration_direction'],
            'ofv_divergence': result['velocity_divergence'],
            'ofv_momentum_score': result['momentum_score'],
            'ofv_persistence': result['velocity_persistence'],
            'ofv_exhaustion': result['velocity_exhaustion']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'velocity_period': [5, 8, 13],
            'acceleration_period': [3, 5, 8],
            'burst_threshold': [1.5, 2.0, 2.5],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
