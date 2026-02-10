"""
544_black_swan_detector.py
===========================
Indicator: Black Swan Detector
Category: Risk Management / Extreme Events
Complexity: Elite

Description:
-----------
Detects conditions that precede black swan events (rare, extreme market moves).
Analyzes market microstructure, volatility clustering, and correlation breakdowns
to identify elevated risk of extreme events.

Key Features:
- Black swan probability
- Pre-event condition detection
- Correlation breakdown analysis
- Extreme event forecasting

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_BlackSwanDetector:
    """
    Black Swan Detector
    
    Detects conditions preceding extreme events.
    """
    
    def __init__(self):
        self.name = "Black Swan Detector"
        self.version = "1.0.0"
        self.category = "Risk Management"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Black Swan Detection metrics
        
        Parameters:
        - detection_period: Period for detection (default: 34)
        - extreme_threshold: Threshold for extreme events (default: 3.0)
        - warning_period: Period for warning signals (default: 13)
        """
        detection_period = params.get('detection_period', 34)
        extreme_threshold = params.get('extreme_threshold', 3.0)
        warning_period = params.get('warning_period', 13)
        
        returns = data['close'].pct_change()
        
        # 1. Extreme Event Detection (>3 sigma moves)
        returns_std = returns.rolling(window=detection_period).std()
        z_score = returns / (returns_std + 1e-10)
        
        extreme_event = (abs(z_score) > extreme_threshold).astype(int)
        
        # 2. Volatility Clustering (GARCH-like)
        # High volatility tends to cluster
        vol_squared = returns**2
        vol_clustering = vol_squared.rolling(window=warning_period).mean() / \
                        vol_squared.rolling(window=detection_period).mean()
        
        # 3. Correlation Breakdown
        # Autocorrelation breaks down before extreme events
        autocorr = returns.rolling(window=detection_period).apply(
            lambda x: abs(np.corrcoef(x[:-1], x[1:])[0, 1]) if len(x) > 1 else 0
        )
        
        correlation_breakdown = (autocorr < 0.2).astype(int)
        
        # 4. Liquidity Stress (volume drying up)
        volume_stress = data['volume'] / data['volume'].rolling(window=detection_period).mean()
        liquidity_stress = (volume_stress < 0.5).astype(int)
        
        # 5. Price Gaps (large gaps indicate stress)
        price_gap = abs(data['open'] - data['close'].shift(1)) / data['close'].shift(1)
        large_gap = (price_gap > 0.01).astype(int)
        
        # 6. Black Swan Probability (composite of warning signals)
        black_swan_probability = (
            vol_clustering * 0.3 +
            correlation_breakdown * 0.25 +
            liquidity_stress * 0.25 +
            large_gap * 0.20
        )
        
        # 7. Warning Level (0=safe, 1=caution, 2=warning, 3=danger)
        warning_level = pd.Series(0, index=data.index)
        warning_level[black_swan_probability > 0.3] = 1
        warning_level[black_swan_probability > 0.5] = 2
        warning_level[black_swan_probability > 0.7] = 3
        
        # 8. Pre-Event Conditions (conditions before extreme events)
        pre_event_conditions = (
            (vol_clustering > 1.5) &
            (correlation_breakdown == 1) &
            (warning_level >= 2)
        ).astype(int)
        
        # 9. Safe Trading Conditions (low black swan risk)
        safe_conditions = (
            (warning_level == 0) &
            (black_swan_probability < 0.2) &
            (extreme_event.rolling(window=warning_period).sum() == 0)
        ).astype(int)
        
        result = pd.DataFrame({
            'z_score': z_score,
            'extreme_event': extreme_event,
            'vol_clustering': vol_clustering,
            'correlation_breakdown': correlation_breakdown,
            'liquidity_stress': liquidity_stress,
            'large_gap': large_gap,
            'black_swan_probability': black_swan_probability,
            'warning_level': warning_level,
            'pre_event_conditions': pre_event_conditions,
            'safe_conditions': safe_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['safe_conditions'] == 1) &
            (result['black_swan_probability'] < 0.2) &
            (result['warning_level'] == 0)
        )
        
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
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
        signal_strength = (1.0 - result['black_swan_probability']).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic Exit Strategy - Indicator-based"""
        result = self.calculate(data, params)
        
        entries = (
            (result['safe_conditions'] == 1) &
            (result['black_swan_probability'] < 0.2) &
            (result['warning_level'] == 0)
        )
        
        exits = (
            (result['warning_level'] >= 2) |
            (result['pre_event_conditions'] == 1) |
            (result['extreme_event'] == 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['warning_level'] >= 2] = 'warning_elevated'
        exit_reason[result['pre_event_conditions'] == 1] = 'pre_event_detected'
        exit_reason[result['extreme_event'] == 1] = 'extreme_event'
        
        signal_strength = (1.0 - result['black_swan_probability']).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extract ML features"""
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'bs_z_score': result['z_score'],
            'bs_extreme_event': result['extreme_event'],
            'bs_vol_clustering': result['vol_clustering'],
            'bs_corr_breakdown': result['correlation_breakdown'],
            'bs_liquidity_stress': result['liquidity_stress'],
            'bs_large_gap': result['large_gap'],
            'bs_probability': result['black_swan_probability'],
            'bs_warning_level': result['warning_level'],
            'bs_pre_event': result['pre_event_conditions'],
            'bs_safe': result['safe_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'detection_period': [34, 55, 89],
            'extreme_threshold': [2.5, 3.0, 3.5],
            'warning_period': [8, 13, 21],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
