"""
542_volatility_targeting_strategy.py
=====================================
Indicator: Volatility Targeting Strategy
Category: Risk Management / Volatility Control
Complexity: Elite

Description:
-----------
Maintains constant volatility exposure by dynamically adjusting position sizes.
Scales up in low volatility, scales down in high volatility. Critical for
stable risk-adjusted returns.

Key Features:
- Volatility forecasting
- Dynamic leverage adjustment
- Target volatility maintenance
- Risk-scaled signals

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_VolatilityTargetingStrategy:
    """
    Volatility Targeting Strategy
    
    Maintains constant volatility exposure.
    """
    
    def __init__(self):
        self.name = "Volatility Targeting Strategy"
        self.version = "1.0.0"
        self.category = "Risk Management"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Volatility Targeting metrics
        
        Parameters:
        - vol_period: Period for volatility calculation (default: 21)
        - target_vol: Target volatility (default: 0.15)
        - forecast_period: Period for volatility forecast (default: 5)
        """
        vol_period = params.get('vol_period', 21)
        target_vol = params.get('target_vol', 0.15)
        forecast_period = params.get('forecast_period', 5)
        
        returns = data['close'].pct_change()
        
        # 1. Realized Volatility
        realized_vol = returns.rolling(window=vol_period).std() * np.sqrt(252)
        
        # 2. Volatility Forecast (EWMA)
        vol_ewma = returns.ewm(span=vol_period).std() * np.sqrt(252)
        
        # 3. Volatility Target Ratio
        vol_target_ratio = target_vol / (realized_vol + 1e-10)
        
        # 4. Position Scaling Factor
        position_scale = vol_target_ratio.clip(0.2, 3.0)  # Limit leverage
        
        # 5. Volatility Regime (1=low, 2=normal, 3=high)
        vol_percentile = realized_vol.rolling(window=vol_period * 2).rank(pct=True)
        
        vol_regime = pd.Series(2, index=data.index)
        vol_regime[vol_percentile < 0.3] = 1  # Low vol
        vol_regime[vol_percentile > 0.7] = 3  # High vol
        
        # 6. Volatility Trend (increasing or decreasing)
        vol_trend = realized_vol.diff(vol_period)
        
        # 7. Optimal Leverage (based on regime)
        optimal_leverage = pd.Series(1.0, index=data.index)
        optimal_leverage[vol_regime == 1] = position_scale[vol_regime == 1]  # Scale up in low vol
        optimal_leverage[vol_regime == 3] = position_scale[vol_regime == 3] * 0.5  # Scale down in high vol
        
        # 8. Risk-Scaled Signal
        base_signal = np.sign(returns.rolling(window=vol_period).sum())
        risk_scaled_signal = base_signal * optimal_leverage
        
        # 9. Volatility Stability (low volatility of volatility)
        vol_of_vol = realized_vol.rolling(window=vol_period).std()
        vol_stability = 1.0 / (vol_of_vol + 1e-10)
        vol_stability_normalized = vol_stability / vol_stability.rolling(window=50).mean()
        
        # 10. Optimal Conditions (stable vol + appropriate regime)
        optimal_conditions = (
            (vol_stability_normalized > 0.8) &
            (vol_regime != 3) &
            (abs(vol_trend) < realized_vol * 0.3)
        ).astype(int)
        
        result = pd.DataFrame({
            'realized_vol': realized_vol,
            'vol_forecast': vol_ewma,
            'vol_target_ratio': vol_target_ratio,
            'position_scale': position_scale,
            'vol_regime': vol_regime,
            'vol_trend': vol_trend,
            'optimal_leverage': optimal_leverage,
            'risk_scaled_signal': risk_scaled_signal,
            'vol_stability': vol_stability_normalized,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['risk_scaled_signal'] > 0) &
            (result['vol_regime'] != 3)
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
        signal_strength = (result['optimal_leverage'] / 3.0).clip(0, 1)
        
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
            (result['optimal_conditions'] == 1) &
            (result['risk_scaled_signal'] > 0) &
            (result['vol_regime'] != 3)
        )
        
        exits = (
            (result['vol_regime'] == 3) |
            (result['risk_scaled_signal'] < 0) |
            (result['vol_stability'] < 0.6)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['vol_regime'] == 3] = 'high_vol_regime'
        exit_reason[result['risk_scaled_signal'] < 0] = 'signal_reversed'
        
        signal_strength = (result['optimal_leverage'] / 3.0).clip(0, 1)
        
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
            'vt_realized_vol': result['realized_vol'],
            'vt_forecast': result['vol_forecast'],
            'vt_target_ratio': result['vol_target_ratio'],
            'vt_position_scale': result['position_scale'],
            'vt_regime': result['vol_regime'],
            'vt_trend': result['vol_trend'],
            'vt_optimal_leverage': result['optimal_leverage'],
            'vt_risk_scaled_signal': result['risk_scaled_signal'],
            'vt_stability': result['vol_stability'],
            'vt_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'risk_period': [13, 21, 34],
            'target_volatility': [0.10, 0.15, 0.20],
            'rebalance_threshold': [0.15, 0.20, 0.25],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
