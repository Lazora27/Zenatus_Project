"""
478_market_maker_spread_compression.py
=======================================
Indicator: Market Maker Spread Compression
Category: Market Microstructure / Market Making
Complexity: Advanced

Description:
-----------
Detects periods of spread compression when market makers reduce bid-ask spreads,
indicating increased competition, improved liquidity, or pre-event positioning.
Spread compression often precedes volatility expansion or directional moves.

Key Features:
- Spread compression ratio
- Compression velocity
- Market maker competition index
- Liquidity improvement score

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 8+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MarketMakerSpreadCompression:
    """
    Market Maker Spread Compression Indicator
    
    Detects spread compression and market maker competition.
    """
    
    def __init__(self):
        self.name = "Market Maker Spread Compression"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Spread Compression metrics
        
        Parameters:
        - spread_period: Period for spread calculation (default: 13)
        - compression_period: Period for compression analysis (default: 21)
        - velocity_period: Period for velocity calculation (default: 5)
        """
        spread_period = params.get('spread_period', 13)
        compression_period = params.get('compression_period', 21)
        velocity_period = params.get('velocity_period', 5)
        
        # Proxy for bid-ask spread: High-Low range
        spread_proxy = data['high'] - data['low']
        
        # Relative spread (spread / midpoint)
        midpoint = (data['high'] + data['low']) / 2
        relative_spread = spread_proxy / (midpoint + 1e-10)
        
        # Average spread
        avg_spread = relative_spread.rolling(window=spread_period).mean()
        
        # Spread compression ratio (current vs historical average)
        historical_avg = relative_spread.rolling(window=compression_period).mean()
        compression_ratio = relative_spread / (historical_avg + 1e-10)
        
        # Compression events (spread significantly below average)
        compression_events = (compression_ratio < 0.7).astype(int)
        
        # Compression velocity (rate of spread narrowing)
        compression_velocity = -relative_spread.pct_change(velocity_period)
        
        # Market maker competition index (inverse of spread volatility)
        spread_volatility = relative_spread.rolling(window=spread_period).std()
        competition_index = 1.0 / (spread_volatility + 1e-10)
        competition_index = competition_index / competition_index.rolling(window=50).mean()
        
        # Liquidity improvement score (compression + volume increase)
        volume_ratio = data['volume'] / data['volume'].rolling(window=spread_period).mean()
        liquidity_improvement = compression_velocity * volume_ratio
        
        # Compression duration (consecutive bars of compression)
        compression_duration = pd.Series(0, index=data.index)
        duration = 0
        for i in range(len(data)):
            if compression_events.iloc[i] == 1:
                duration += 1
            else:
                duration = 0
            compression_duration.iloc[i] = duration
        
        # Spread stability (low volatility = stable spreads)
        spread_stability = 1.0 / (spread_volatility / (avg_spread + 1e-10) + 1e-10)
        spread_stability = spread_stability / spread_stability.rolling(window=50).mean()
        
        # Pre-event indicator (extreme compression often precedes moves)
        pre_event_score = (
            (compression_ratio < 0.6).astype(int) * 
            (compression_duration > 3).astype(int)
        )
        
        result = pd.DataFrame({
            'spread_proxy': spread_proxy,
            'relative_spread': relative_spread,
            'compression_ratio': compression_ratio,
            'compression_events': compression_events,
            'compression_velocity': compression_velocity,
            'competition_index': competition_index,
            'liquidity_improvement': liquidity_improvement,
            'compression_duration': compression_duration,
            'spread_stability': spread_stability,
            'pre_event_score': pre_event_score
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When spread compression detected with high liquidity improvement
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Compression event + positive velocity + liquidity improvement
        entries = (
            (result['compression_events'] == 1) &
            (result['compression_velocity'] > 0.05) &
            (result['liquidity_improvement'] > 0) &
            (result['competition_index'] > 1.2)
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
        
        # Signal strength based on compression velocity and competition
        signal_strength = (result['compression_velocity'] * result['competition_index']).clip(0, 1)
        
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
        
        Entry: Spread compression detected
        Exit: When compression ends or pre-event score triggers
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['compression_events'] == 1) &
            (result['compression_velocity'] > 0.05) &
            (result['liquidity_improvement'] > 0) &
            (result['competition_index'] > 1.2)
        )
        
        # Exit: Compression ends or pre-event score triggers (volatility expansion coming)
        exits = (
            (result['compression_events'] == 0) |
            (result['pre_event_score'] == 1) |
            (result['compression_velocity'] < -0.05)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['compression_events'] == 0] = 'compression_ended'
        exit_reason[result['pre_event_score'] == 1] = 'pre_event_trigger'
        exit_reason[result['compression_velocity'] < -0.05] = 'spread_expansion'
        
        signal_strength = (result['compression_velocity'] * result['competition_index']).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 10 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'mm_spread_relative': result['relative_spread'],
            'mm_compression_ratio': result['compression_ratio'],
            'mm_compression_events': result['compression_events'],
            'mm_compression_velocity': result['compression_velocity'],
            'mm_competition_index': result['competition_index'],
            'mm_liquidity_improvement': result['liquidity_improvement'],
            'mm_compression_duration': result['compression_duration'],
            'mm_spread_stability': result['spread_stability'],
            'mm_pre_event_score': result['pre_event_score'],
            'mm_compression_intensity': result['compression_velocity'] * result['compression_events']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'spread_period': [8, 13, 21],
            'compression_period': [13, 21, 34],
            'velocity_period': [3, 5, 8],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
