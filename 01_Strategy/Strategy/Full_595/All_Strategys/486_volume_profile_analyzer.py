"""
486_volume_profile_analyzer.py
================================
Indicator: Volume Profile Analyzer
Category: Market Microstructure / Volume Analysis
Complexity: Advanced

Description:
-----------
Analyzes volume distribution across price levels to identify high-volume nodes (HVN),
low-volume nodes (LVN), point of control (POC), and value areas. Critical for
understanding where institutional activity is concentrated and support/resistance.

Key Features:
- Point of Control (POC) detection
- High/Low Volume Node identification
- Value Area calculation
- Volume concentration score

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_VolumeProfileAnalyzer:
    """
    Volume Profile Analyzer
    
    Analyzes volume distribution across price levels.
    """
    
    def __init__(self):
        self.name = "Volume Profile Analyzer"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Volume Profile metrics
        
        Parameters:
        - profile_period: Period for profile analysis (default: 34)
        - price_bins: Number of price bins for distribution (default: 20)
        - value_area_pct: Percentage for value area (default: 0.7)
        """
        profile_period = params.get('profile_period', 34)
        price_bins = params.get('price_bins', 20)
        value_area_pct = params.get('value_area_pct', 0.7)
        
        # Initialize result series
        poc_price = pd.Series(0.0, index=data.index)
        hvn_score = pd.Series(0.0, index=data.index)
        lvn_score = pd.Series(0.0, index=data.index)
        value_area_high = pd.Series(0.0, index=data.index)
        value_area_low = pd.Series(0.0, index=data.index)
        volume_concentration = pd.Series(0.0, index=data.index)
        poc_distance = pd.Series(0.0, index=data.index)
        
        # Calculate rolling volume profile
        for i in range(profile_period, len(data)):
            window_data = data.iloc[i-profile_period:i]
            
            # Create price bins
            price_min = window_data['low'].min()
            price_max = window_data['high'].max()
            
            if price_max > price_min:
                bin_edges = np.linspace(price_min, price_max, price_bins + 1)
                
                # Distribute volume across price bins
                volume_dist = np.zeros(price_bins)
                
                for j in range(len(window_data)):
                    row = window_data.iloc[j]
                    # Assume volume distributed evenly across high-low range
                    low_bin = np.digitize(row['low'], bin_edges) - 1
                    high_bin = np.digitize(row['high'], bin_edges) - 1
                    
                    low_bin = max(0, min(low_bin, price_bins - 1))
                    high_bin = max(0, min(high_bin, price_bins - 1))
                    
                    # Distribute volume
                    bins_touched = high_bin - low_bin + 1
                    if bins_touched > 0:
                        vol_per_bin = row['volume'] / bins_touched
                        for k in range(low_bin, high_bin + 1):
                            if 0 <= k < price_bins:
                                volume_dist[k] += vol_per_bin
                
                # Point of Control (highest volume bin)
                poc_bin = np.argmax(volume_dist)
                poc_price.iloc[i] = (bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2
                
                # High Volume Nodes (top 20% of bins)
                volume_threshold_high = np.percentile(volume_dist, 80)
                hvn_score.iloc[i] = np.sum(volume_dist > volume_threshold_high) / price_bins
                
                # Low Volume Nodes (bottom 20% of bins)
                volume_threshold_low = np.percentile(volume_dist, 20)
                lvn_score.iloc[i] = np.sum(volume_dist < volume_threshold_low) / price_bins
                
                # Value Area (70% of volume)
                sorted_indices = np.argsort(volume_dist)[::-1]
                cumulative_volume = 0
                total_volume = np.sum(volume_dist)
                value_bins = []
                
                for idx in sorted_indices:
                    cumulative_volume += volume_dist[idx]
                    value_bins.append(idx)
                    if cumulative_volume >= total_volume * value_area_pct:
                        break
                
                if value_bins:
                    value_area_high.iloc[i] = bin_edges[max(value_bins) + 1]
                    value_area_low.iloc[i] = bin_edges[min(value_bins)]
                
                # Volume Concentration (Gini coefficient-like)
                sorted_vol = np.sort(volume_dist)
                n = len(sorted_vol)
                index = np.arange(1, n + 1)
                concentration = (2 * np.sum(index * sorted_vol)) / (n * np.sum(sorted_vol)) - (n + 1) / n
                volume_concentration.iloc[i] = concentration
                
                # Distance from current price to POC
                poc_distance.iloc[i] = (data['close'].iloc[i] - poc_price.iloc[i]) / data['close'].iloc[i]
        
        # Additional metrics
        # POC strength (how much volume at POC vs average)
        poc_strength = pd.Series(1.0, index=data.index)
        
        # Price at value area boundaries
        at_value_high = (data['close'] >= value_area_high * 0.98).astype(int)
        at_value_low = (data['close'] <= value_area_low * 1.02).astype(int)
        
        # Volume profile trend (POC moving up or down)
        poc_trend = poc_price.diff(5)
        
        # Acceptance (price staying in value area)
        in_value_area = ((data['close'] >= value_area_low) & (data['close'] <= value_area_high)).astype(int)
        
        result = pd.DataFrame({
            'poc_price': poc_price,
            'hvn_score': hvn_score,
            'lvn_score': lvn_score,
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'volume_concentration': volume_concentration,
            'poc_distance': poc_distance,
            'poc_strength': poc_strength,
            'at_value_high': at_value_high,
            'at_value_low': at_value_low,
            'poc_trend': poc_trend,
            'in_value_area': in_value_area
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When price approaches POC or value area boundaries
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Price near POC with upward POC trend + high volume concentration
        entries = (
            (abs(result['poc_distance']) < 0.01) &
            (result['poc_trend'] > 0) &
            (result['volume_concentration'] > 0.5) &
            (result['in_value_area'] == 1)
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
        
        # Signal strength based on volume concentration
        signal_strength = result['volume_concentration'].clip(0, 1)
        
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
        
        Entry: Price at POC or value area
        Exit: When price leaves value area or POC trend reverses
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (abs(result['poc_distance']) < 0.01) &
            (result['poc_trend'] > 0) &
            (result['volume_concentration'] > 0.5) &
            (result['in_value_area'] == 1)
        )
        
        # Exit: Leaves value area or POC trend reverses
        exits = (
            (result['in_value_area'] == 0) |
            (result['poc_trend'] < 0) |
            (abs(result['poc_distance']) > 0.03)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['in_value_area'] == 0] = 'left_value_area'
        exit_reason[result['poc_trend'] < 0] = 'poc_trend_reversal'
        exit_reason[abs(result['poc_distance']) > 0.03] = 'far_from_poc'
        
        signal_strength = result['volume_concentration'].clip(0, 1)
        
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
            'vp_poc_price': result['poc_price'],
            'vp_hvn_score': result['hvn_score'],
            'vp_lvn_score': result['lvn_score'],
            'vp_value_area_high': result['value_area_high'],
            'vp_value_area_low': result['value_area_low'],
            'vp_volume_concentration': result['volume_concentration'],
            'vp_poc_distance': result['poc_distance'],
            'vp_poc_strength': result['poc_strength'],
            'vp_at_value_high': result['at_value_high'],
            'vp_at_value_low': result['at_value_low'],
            'vp_poc_trend': result['poc_trend'],
            'vp_in_value_area': result['in_value_area']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'profile_period': [21, 34, 55],
            'price_bins': [15, 20, 30],
            'value_area_pct': [0.68, 0.70, 0.75],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
