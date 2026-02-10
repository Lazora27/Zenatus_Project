"""
489_price_level_magnetism.py
=============================
Indicator: Price Level Magnetism
Category: Market Microstructure / Price Action
Complexity: Advanced

Description:
-----------
Identifies price levels that act as "magnets" attracting price action. Detects
psychological levels, round numbers, previous highs/lows, and areas where price
tends to gravitate. Critical for understanding price behavior near key levels.

Key Features:
- Magnetic level detection
- Attraction strength measurement
- Level rejection/acceptance
- Magnetism momentum

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_PriceLevelMagnetism:
    """
    Price Level Magnetism Indicator
    
    Identifies magnetic price levels and attraction dynamics.
    """
    
    def __init__(self):
        self.name = "Price Level Magnetism"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Price Level Magnetism metrics
        
        Parameters:
        - magnetism_period: Period for magnetism analysis (default: 34)
        - level_period: Period for level identification (default: 55)
        - attraction_threshold: Distance threshold for attraction (default: 0.005)
        """
        magnetism_period = params.get('magnetism_period', 34)
        level_period = params.get('level_period', 55)
        attraction_threshold = params.get('attraction_threshold', 0.005)
        
        # 1. Identify Key Levels (recent highs/lows)
        rolling_high = data['high'].rolling(window=level_period).max()
        rolling_low = data['low'].rolling(window=level_period).min()
        
        # 2. Round Number Levels (psychological levels)
        # Detect proximity to round numbers (multiples of 100, 50, etc.)
        price_rounded_100 = (data['close'] / 100).round() * 100
        price_rounded_50 = (data['close'] / 50).round() * 50
        price_rounded_10 = (data['close'] / 10).round() * 10
        
        # Distance to nearest round number
        dist_to_100 = abs(data['close'] - price_rounded_100) / data['close']
        dist_to_50 = abs(data['close'] - price_rounded_50) / data['close']
        dist_to_10 = abs(data['close'] - price_rounded_10) / data['close']
        
        # Minimum distance to any round number
        dist_to_round = pd.concat([dist_to_100, dist_to_50, dist_to_10], axis=1).min(axis=1)
        
        # 3. Near Round Number (magnetic level)
        near_round_number = (dist_to_round < attraction_threshold).astype(int)
        
        # 4. Distance to Key Levels
        dist_to_high = (rolling_high - data['close']) / data['close']
        dist_to_low = (data['close'] - rolling_low) / data['close']
        
        # 5. Attraction to High/Low
        attracted_to_high = (dist_to_high < attraction_threshold).astype(int)
        attracted_to_low = (dist_to_low < attraction_threshold).astype(int)
        
        # 6. Magnetism Strength (how often price returns to level)
        # Count touches of key levels
        touches_high = (data['high'] >= rolling_high * 0.995).astype(int)
        touches_low = (data['low'] <= rolling_low * 1.005).astype(int)
        
        magnetism_strength_high = touches_high.rolling(window=magnetism_period).sum()
        magnetism_strength_low = touches_low.rolling(window=magnetism_period).sum()
        
        # 7. Level Acceptance/Rejection
        # Acceptance: Price stays near level
        # Rejection: Price bounces away
        price_velocity = abs(data['close'].pct_change(3))
        
        level_rejection = (
            ((attracted_to_high == 1) | (attracted_to_low == 1)) &
            (price_velocity > price_velocity.rolling(window=magnetism_period).quantile(0.7))
        ).astype(int)
        
        level_acceptance = (
            ((attracted_to_high == 1) | (attracted_to_low == 1)) &
            (price_velocity < price_velocity.rolling(window=magnetism_period).quantile(0.3))
        ).astype(int)
        
        # 8. Magnetism Momentum (speed of approach to level)
        approach_velocity = pd.Series(0.0, index=data.index)
        approach_velocity[dist_to_high < dist_to_high.shift(1)] = -dist_to_high.diff()
        approach_velocity[dist_to_low < dist_to_low.shift(1)] = -dist_to_low.diff()
        
        # 9. Magnetic Pull Score (composite)
        magnetic_pull = (
            near_round_number * 0.3 +
            attracted_to_high * 0.25 +
            attracted_to_low * 0.25 +
            (magnetism_strength_high / magnetism_period) * 0.1 +
            (magnetism_strength_low / magnetism_period) * 0.1
        )
        
        # 10. Level Clustering (multiple levels nearby)
        level_density = (
            near_round_number +
            attracted_to_high +
            attracted_to_low
        )
        
        # 11. Breakout Probability (near level with high volatility)
        volatility = data['close'].pct_change().rolling(window=magnetism_period).std()
        breakout_probability = magnetic_pull * (volatility / volatility.rolling(window=50).mean())
        
        result = pd.DataFrame({
            'rolling_high': rolling_high,
            'rolling_low': rolling_low,
            'dist_to_round': dist_to_round,
            'near_round_number': near_round_number,
            'dist_to_high': dist_to_high,
            'dist_to_low': dist_to_low,
            'attracted_to_high': attracted_to_high,
            'attracted_to_low': attracted_to_low,
            'magnetism_strength_high': magnetism_strength_high,
            'magnetism_strength_low': magnetism_strength_low,
            'level_rejection': level_rejection,
            'level_acceptance': level_acceptance,
            'approach_velocity': approach_velocity,
            'magnetic_pull': magnetic_pull,
            'level_density': level_density,
            'breakout_probability': breakout_probability
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When price near magnetic level with acceptance
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Near magnetic level + acceptance + high magnetism strength
        entries = (
            (result['magnetic_pull'] > 0.5) &
            (result['level_acceptance'] == 1) &
            ((result['magnetism_strength_high'] > 3) | (result['magnetism_strength_low'] > 3)) &
            (result['approach_velocity'] > 0)
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
        
        # Signal strength based on magnetic pull
        signal_strength = result['magnetic_pull'].clip(0, 1)
        
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
        
        Entry: Near magnetic level
        Exit: When level rejected or magnetic pull weakens
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['magnetic_pull'] > 0.5) &
            (result['level_acceptance'] == 1) &
            ((result['magnetism_strength_high'] > 3) | (result['magnetism_strength_low'] > 3)) &
            (result['approach_velocity'] > 0)
        )
        
        # Exit: Level rejection or magnetic pull weakens
        exits = (
            (result['level_rejection'] == 1) |
            (result['magnetic_pull'] < 0.3) |
            (result['breakout_probability'] > 1.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['level_rejection'] == 1] = 'level_rejected'
        exit_reason[result['magnetic_pull'] < 0.3] = 'magnetism_weakened'
        exit_reason[result['breakout_probability'] > 1.5] = 'breakout_likely'
        
        signal_strength = result['magnetic_pull'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 16 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'plm_rolling_high': result['rolling_high'],
            'plm_rolling_low': result['rolling_low'],
            'plm_dist_to_round': result['dist_to_round'],
            'plm_near_round_number': result['near_round_number'],
            'plm_dist_to_high': result['dist_to_high'],
            'plm_dist_to_low': result['dist_to_low'],
            'plm_attracted_to_high': result['attracted_to_high'],
            'plm_attracted_to_low': result['attracted_to_low'],
            'plm_magnetism_high': result['magnetism_strength_high'],
            'plm_magnetism_low': result['magnetism_strength_low'],
            'plm_level_rejection': result['level_rejection'],
            'plm_level_acceptance': result['level_acceptance'],
            'plm_approach_velocity': result['approach_velocity'],
            'plm_magnetic_pull': result['magnetic_pull'],
            'plm_level_density': result['level_density'],
            'plm_breakout_probability': result['breakout_probability']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'magnetism_period': [21, 34, 55],
            'level_period': [34, 55, 89],
            'attraction_threshold': [0.003, 0.005, 0.01],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
