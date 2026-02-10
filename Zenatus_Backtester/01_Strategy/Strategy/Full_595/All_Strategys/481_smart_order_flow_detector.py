"""
481_smart_order_flow_detector.py
==================================
Indicator: Smart Order Flow Detector
Category: Market Microstructure / Institutional Flow
Complexity: Advanced

Description:
-----------
Identifies intelligent order flow from institutional traders and smart money.
Distinguishes between informed trading and noise by analyzing order characteristics,
execution patterns, and price impact persistence. Critical for following smart money.

Key Features:
- Smart money flow score
- Institutional footprint detection
- Order sophistication index
- Informed trading probability

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_SmartOrderFlowDetector:
    """
    Smart Order Flow Detector
    
    Identifies intelligent institutional order flow.
    """
    
    def __init__(self):
        self.name = "Smart Order Flow Detector"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Smart Order Flow metrics
        
        Parameters:
        - flow_period: Period for flow analysis (default: 21)
        - impact_period: Period for impact measurement (default: 13)
        - sophistication_period: Period for sophistication analysis (default: 34)
        """
        flow_period = params.get('flow_period', 21)
        impact_period = params.get('impact_period', 13)
        sophistication_period = params.get('sophistication_period', 34)
        
        # 1. Persistent Price Impact (smart money moves prices permanently)
        price_change = data['close'].pct_change()
        volume_signed = data['volume'] * np.sign(price_change)
        
        # Immediate impact
        immediate_impact = abs(price_change)
        
        # Persistent impact (price change after N bars)
        persistent_impact = abs(data['close'].pct_change(impact_period))
        
        # Impact persistence ratio (high = smart money)
        impact_persistence = persistent_impact / (immediate_impact + 1e-10)
        impact_persistence = impact_persistence.rolling(window=flow_period).mean()
        
        # 2. Order Sophistication Index (gradual accumulation vs aggressive buying)
        volume_volatility = data['volume'].rolling(window=flow_period).std()
        volume_mean = data['volume'].rolling(window=flow_period).mean()
        volume_smoothness = 1.0 / (volume_volatility / (volume_mean + 1e-10) + 1e-10)
        
        # Price stability during accumulation (low volatility = sophisticated)
        price_volatility = data['close'].pct_change().rolling(window=flow_period).std()
        sophistication_index = volume_smoothness / (price_volatility + 1e-10)
        sophistication_index = sophistication_index / sophistication_index.rolling(window=50).mean()
        
        # 3. Informed Trading Probability (PIN-like metric)
        buy_volume = volume_signed.where(volume_signed > 0, 0)
        sell_volume = abs(volume_signed.where(volume_signed < 0, 0))
        
        volume_imbalance = abs(buy_volume - sell_volume) / (data['volume'] + 1e-10)
        informed_probability = volume_imbalance.rolling(window=flow_period).mean()
        
        # 4. Institutional Footprint (large orders with minimal slippage)
        # Proxy: High volume with low price impact
        volume_percentile = data['volume'].rolling(window=sophistication_period).rank(pct=True)
        price_impact_percentile = immediate_impact.rolling(window=sophistication_period).rank(pct=True)
        
        institutional_footprint = (volume_percentile > 0.8).astype(int) * (price_impact_percentile < 0.5).astype(int)
        
        # 5. Smart Money Flow Score (composite)
        smart_flow_score = (
            impact_persistence * 0.3 +
            sophistication_index * 0.25 +
            informed_probability * 0.25 +
            institutional_footprint * 0.2
        )
        
        # Normalize
        smart_flow_normalized = smart_flow_score / (smart_flow_score.rolling(window=50).mean() + 1e-10)
        
        # 6. Flow Direction (buy vs sell pressure)
        flow_direction = np.sign(buy_volume - sell_volume)
        
        # 7. Smart Money Events (high score periods)
        smart_events = (smart_flow_normalized > 1.5).astype(int)
        
        # 8. Accumulation/Distribution Phase
        cumulative_flow = (buy_volume - sell_volume).rolling(window=sophistication_period).sum()
        accumulation_phase = (cumulative_flow > 0).astype(int)  # 1 = accumulation, 0 = distribution
        
        # 9. Order Execution Quality (VWAP deviation)
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwap = (typical_price * data['volume']).rolling(window=flow_period).sum() / \
               data['volume'].rolling(window=flow_period).sum()
        execution_quality = 1.0 - abs(data['close'] - vwap) / (vwap + 1e-10)
        
        # 10. Smart Money Confidence (consistency of flow)
        flow_consistency = smart_flow_score.rolling(window=flow_period).apply(
            lambda x: len(x[x > x.mean()]) / len(x) if len(x) > 0 else 0.5
        )
        
        result = pd.DataFrame({
            'impact_persistence': impact_persistence,
            'sophistication_index': sophistication_index,
            'informed_probability': informed_probability,
            'institutional_footprint': institutional_footprint,
            'smart_flow_score': smart_flow_score,
            'smart_flow_normalized': smart_flow_normalized,
            'flow_direction': flow_direction,
            'smart_events': smart_events,
            'accumulation_phase': accumulation_phase,
            'execution_quality': execution_quality,
            'flow_consistency': flow_consistency
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When smart money flow detected with high confidence
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Smart event + positive flow direction + high sophistication + accumulation
        entries = (
            (result['smart_events'] == 1) &
            (result['flow_direction'] > 0) &
            (result['sophistication_index'] > 1.2) &
            (result['accumulation_phase'] == 1) &
            (result['flow_consistency'] > 0.6)
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
        
        # Signal strength based on smart flow score
        signal_strength = result['smart_flow_normalized'] / 3.0
        signal_strength = signal_strength.clip(0, 1)
        
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
        
        Entry: Smart money flow detected
        Exit: When flow reverses or confidence drops
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['smart_events'] == 1) &
            (result['flow_direction'] > 0) &
            (result['sophistication_index'] > 1.2) &
            (result['accumulation_phase'] == 1) &
            (result['flow_consistency'] > 0.6)
        )
        
        # Exit: Flow direction reverses or confidence drops
        exits = (
            (result['flow_direction'] < 0) |
            (result['accumulation_phase'] == 0) |
            (result['flow_consistency'] < 0.4) |
            (result['smart_flow_normalized'] < 0.8)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['flow_direction'] < 0] = 'flow_reversal'
        exit_reason[result['accumulation_phase'] == 0] = 'distribution_phase'
        exit_reason[result['flow_consistency'] < 0.4] = 'confidence_drop'
        
        signal_strength = result['smart_flow_normalized'] / 3.0
        signal_strength = signal_strength.clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 11 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'smart_flow_impact_persistence': result['impact_persistence'],
            'smart_flow_sophistication': result['sophistication_index'],
            'smart_flow_informed_prob': result['informed_probability'],
            'smart_flow_institutional': result['institutional_footprint'],
            'smart_flow_score': result['smart_flow_score'],
            'smart_flow_normalized': result['smart_flow_normalized'],
            'smart_flow_direction': result['flow_direction'],
            'smart_flow_events': result['smart_events'],
            'smart_flow_accumulation': result['accumulation_phase'],
            'smart_flow_execution_quality': result['execution_quality'],
            'smart_flow_consistency': result['flow_consistency']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'flow_period': [13, 21, 34],
            'impact_period': [8, 13, 21],
            'sophistication_period': [21, 34, 55],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
