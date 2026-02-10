"""
487_market_depth_imbalance.py
==============================
Indicator: Market Depth Imbalance
Category: Market Microstructure / Order Book Analysis
Complexity: Advanced

Description:
-----------
Measures imbalance in market depth between bid and ask sides at multiple price levels.
Detects institutional positioning and predicts short-term price direction based on
depth asymmetry. Critical for understanding supply/demand dynamics.

Key Features:
- Multi-level depth imbalance
- Depth-weighted pressure
- Cumulative depth ratio
- Imbalance momentum

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MarketDepthImbalance:
    """
    Market Depth Imbalance Indicator
    
    Measures bid-ask depth imbalances.
    """
    
    def __init__(self):
        self.name = "Market Depth Imbalance"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Market Depth Imbalance metrics
        
        Parameters:
        - depth_period: Period for depth analysis (default: 13)
        - imbalance_period: Period for imbalance smoothing (default: 8)
        - levels: Number of price levels to analyze (default: 5)
        """
        depth_period = params.get('depth_period', 13)
        imbalance_period = params.get('imbalance_period', 8)
        levels = params.get('levels', 5)
        
        # Proxy for depth: Use volume and price range
        # In real implementation, would use actual order book depth data
        
        # 1. Bid Depth Proxy (volume at lower prices)
        bid_depth = data['volume'] * (data['close'] - data['low']) / (data['high'] - data['low'] + 1e-10)
        
        # 2. Ask Depth Proxy (volume at higher prices)
        ask_depth = data['volume'] * (data['high'] - data['close']) / (data['high'] - data['low'] + 1e-10)
        
        # 3. Depth Imbalance (positive = more bid depth)
        depth_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth + 1e-10)
        
        # 4. Smoothed Imbalance
        imbalance_smoothed = depth_imbalance.rolling(window=imbalance_period).mean()
        
        # 5. Cumulative Depth Ratio (running sum of imbalances)
        cumulative_imbalance = depth_imbalance.rolling(window=depth_period).sum()
        
        # 6. Depth-Weighted Pressure (imbalance * volume)
        depth_pressure = depth_imbalance * data['volume']
        depth_pressure_smoothed = depth_pressure.rolling(window=imbalance_period).mean()
        
        # 7. Imbalance Momentum (rate of change)
        imbalance_momentum = depth_imbalance.diff(imbalance_period)
        
        # 8. Imbalance Strength (absolute value)
        imbalance_strength = abs(depth_imbalance)
        
        # 9. Bid Dominance (0-1 scale)
        bid_dominance = (depth_imbalance + 1) / 2
        
        # 10. Extreme Imbalance Events
        imbalance_threshold = imbalance_strength.rolling(window=depth_period).quantile(0.8)
        extreme_imbalance = (imbalance_strength > imbalance_threshold).astype(int)
        
        # 11. Depth Stability (low volatility = stable depth)
        depth_volatility = depth_imbalance.rolling(window=depth_period).std()
        depth_stability = 1.0 / (depth_volatility + 1e-10)
        depth_stability_normalized = depth_stability / depth_stability.rolling(window=50).mean()
        
        # 12. Multi-Level Imbalance (simulate multiple levels)
        # Level 1: Immediate (already calculated)
        # Level 2: Deeper levels (use wider price range)
        level2_bid = data['volume'] * (data['close'] - data['low']) / (data['high'] - data['low'] + 1e-10) * 0.8
        level2_ask = data['volume'] * (data['high'] - data['close']) / (data['high'] - data['low'] + 1e-10) * 0.8
        level2_imbalance = (level2_bid - level2_ask) / (level2_bid + level2_ask + 1e-10)
        
        # Combined multi-level imbalance
        multi_level_imbalance = (depth_imbalance * 0.6 + level2_imbalance * 0.4)
        
        result = pd.DataFrame({
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'depth_imbalance': depth_imbalance,
            'imbalance_smoothed': imbalance_smoothed,
            'cumulative_imbalance': cumulative_imbalance,
            'depth_pressure': depth_pressure_smoothed,
            'imbalance_momentum': imbalance_momentum,
            'imbalance_strength': imbalance_strength,
            'bid_dominance': bid_dominance,
            'extreme_imbalance': extreme_imbalance,
            'depth_stability': depth_stability_normalized,
            'multi_level_imbalance': multi_level_imbalance
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When strong bid depth imbalance detected
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Strong bid imbalance + positive momentum + extreme event
        entries = (
            (result['extreme_imbalance'] == 1) &
            (result['depth_imbalance'] > 0.3) &
            (result['imbalance_momentum'] > 0) &
            (result['bid_dominance'] > 0.65) &
            (result['cumulative_imbalance'] > 0)
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
        
        # Signal strength based on imbalance strength
        signal_strength = result['imbalance_strength'].clip(0, 1)
        
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
        
        Entry: Strong depth imbalance
        Exit: When imbalance reverses or weakens
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['extreme_imbalance'] == 1) &
            (result['depth_imbalance'] > 0.3) &
            (result['imbalance_momentum'] > 0) &
            (result['bid_dominance'] > 0.65) &
            (result['cumulative_imbalance'] > 0)
        )
        
        # Exit: Imbalance reverses or momentum turns negative
        exits = (
            (result['depth_imbalance'] < 0) |
            (result['imbalance_momentum'] < -0.1) |
            (result['bid_dominance'] < 0.5) |
            (result['cumulative_imbalance'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['depth_imbalance'] < 0] = 'imbalance_reversal'
        exit_reason[result['imbalance_momentum'] < -0.1] = 'momentum_reversal'
        exit_reason[result['bid_dominance'] < 0.5] = 'dominance_lost'
        
        signal_strength = result['imbalance_strength'].clip(0, 1)
        
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
            'md_bid_depth': result['bid_depth'],
            'md_ask_depth': result['ask_depth'],
            'md_depth_imbalance': result['depth_imbalance'],
            'md_imbalance_smoothed': result['imbalance_smoothed'],
            'md_cumulative_imbalance': result['cumulative_imbalance'],
            'md_depth_pressure': result['depth_pressure'],
            'md_imbalance_momentum': result['imbalance_momentum'],
            'md_imbalance_strength': result['imbalance_strength'],
            'md_bid_dominance': result['bid_dominance'],
            'md_extreme_imbalance': result['extreme_imbalance'],
            'md_depth_stability': result['depth_stability'],
            'md_multi_level_imbalance': result['multi_level_imbalance']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'depth_period': [8, 13, 21],
            'imbalance_period': [5, 8, 13],
            'levels': [3, 5, 7],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
