"""
477_order_flow_persistence.py
==============================
Indicator: Order Flow Persistence
Category: Market Microstructure / Order Flow Analysis
Complexity: Advanced

Description:
-----------
Measures the persistence and autocorrelation of order flow imbalances. Identifies
sustained directional pressure from institutional orders and distinguishes between
temporary noise and persistent trends. Uses Hurst exponent and autocorrelation.

Key Features:
- Order flow autocorrelation
- Persistence score (Hurst-like metric)
- Directional consistency
- Mean reversion tendency

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 8+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_OrderFlowPersistence:
    """
    Order Flow Persistence Indicator
    
    Measures persistence and autocorrelation of order flow.
    """
    
    def __init__(self):
        self.name = "Order Flow Persistence"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Order Flow Persistence metrics
        
        Parameters:
        - flow_period: Period for flow calculation (default: 13)
        - persistence_period: Period for persistence analysis (default: 21)
        - autocorr_lags: Lags for autocorrelation (default: 5)
        """
        flow_period = params.get('flow_period', 13)
        persistence_period = params.get('persistence_period', 21)
        autocorr_lags = params.get('autocorr_lags', 5)
        
        # Calculate order flow proxy (signed volume)
        price_change = data['close'].diff()
        signed_volume = data['volume'] * np.sign(price_change)
        
        # Order flow imbalance
        flow_imbalance = signed_volume.rolling(window=flow_period).sum()
        
        # Autocorrelation at lag 1
        flow_autocorr = flow_imbalance.rolling(window=persistence_period).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0
        )
        
        # Multi-lag autocorrelation (average of multiple lags)
        multi_lag_autocorr = pd.Series(0.0, index=data.index)
        for lag in range(1, autocorr_lags + 1):
            lag_corr = flow_imbalance.rolling(window=persistence_period).apply(
                lambda x: np.corrcoef(x[:-lag], x[lag:])[0, 1] if len(x) > lag else 0
            )
            multi_lag_autocorr += lag_corr
        multi_lag_autocorr /= autocorr_lags
        
        # Persistence score (simplified Hurst-like metric)
        # Range / StdDev ratio
        flow_range = flow_imbalance.rolling(window=persistence_period).max() - \
                     flow_imbalance.rolling(window=persistence_period).min()
        flow_std = flow_imbalance.rolling(window=persistence_period).std()
        persistence_score = flow_range / (flow_std + 1e-10)
        
        # Normalize persistence score (0.5 = random walk, >0.5 = persistent, <0.5 = mean reverting)
        persistence_normalized = persistence_score / (persistence_score.rolling(window=50).mean() + 1e-10)
        
        # Directional consistency (% of same-sign flows)
        directional_consistency = flow_imbalance.rolling(window=persistence_period).apply(
            lambda x: np.sum(x > 0) / len(x) if len(x) > 0 else 0.5
        )
        
        # Mean reversion tendency (negative autocorrelation indicates mean reversion)
        mean_reversion = -flow_autocorr
        
        # Flow momentum (acceleration of flow)
        flow_momentum = flow_imbalance.diff(flow_period)
        
        # Persistence regime (1 = persistent, 0 = random, -1 = mean reverting)
        persistence_regime = pd.Series(0, index=data.index)
        persistence_regime[persistence_normalized > 1.2] = 1
        persistence_regime[persistence_normalized < 0.8] = -1
        
        result = pd.DataFrame({
            'flow_imbalance': flow_imbalance,
            'flow_autocorr': flow_autocorr,
            'multi_lag_autocorr': multi_lag_autocorr,
            'persistence_score': persistence_score,
            'persistence_normalized': persistence_normalized,
            'directional_consistency': directional_consistency,
            'mean_reversion': mean_reversion,
            'flow_momentum': flow_momentum,
            'persistence_regime': persistence_regime
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When order flow shows high persistence with positive momentum
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: High persistence + positive flow momentum + high directional consistency
        entries = (
            (result['persistence_regime'] == 1) &
            (result['flow_momentum'] > 0) &
            (result['directional_consistency'] > 0.6) &
            (result['flow_autocorr'] > 0.3)
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
        
        # Signal strength based on persistence and autocorrelation
        signal_strength = (result['flow_autocorr'] + result['persistence_normalized']) / 2.0
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
        
        Entry: High persistence detected
        Exit: When persistence breaks down or regime changes
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['persistence_regime'] == 1) &
            (result['flow_momentum'] > 0) &
            (result['directional_consistency'] > 0.6) &
            (result['flow_autocorr'] > 0.3)
        )
        
        # Exit: Persistence regime changes or autocorrelation turns negative
        exits = (
            (result['persistence_regime'] != 1) |
            (result['flow_autocorr'] < 0) |
            (result['directional_consistency'] < 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['persistence_regime'] != 1] = 'regime_change'
        exit_reason[result['flow_autocorr'] < 0] = 'negative_autocorr'
        exit_reason[result['directional_consistency'] < 0.5] = 'consistency_breakdown'
        
        signal_strength = (result['flow_autocorr'] + result['persistence_normalized']) / 2.0
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
        
        Returns 9 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'flow_persistence_imbalance': result['flow_imbalance'],
            'flow_persistence_autocorr': result['flow_autocorr'],
            'flow_persistence_multi_lag': result['multi_lag_autocorr'],
            'flow_persistence_score': result['persistence_score'],
            'flow_persistence_normalized': result['persistence_normalized'],
            'flow_directional_consistency': result['directional_consistency'],
            'flow_mean_reversion': result['mean_reversion'],
            'flow_momentum': result['flow_momentum'],
            'flow_persistence_regime': result['persistence_regime']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'flow_period': [8, 13, 21],
            'persistence_period': [13, 21, 34],
            'autocorr_lags': [3, 5, 8],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
