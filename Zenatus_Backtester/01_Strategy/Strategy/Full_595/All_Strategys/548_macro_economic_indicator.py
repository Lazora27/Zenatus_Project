"""
548_macro_economic_indicator.py
================================
Indicator: Macro Economic Indicator
Category: Master Indicators / Macro Analysis
Complexity: Elite

Description:
-----------
Synthesizes macro-economic signals from price action. Uses price trends,
volatility, and volume as proxies for economic conditions. Detects
expansion/contraction cycles.

Key Features:
- Economic cycle detection
- Growth/contraction signals
- Macro regime classification
- Leading indicator synthesis

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MacroEconomicIndicator:
    """
    Macro Economic Indicator
    
    Synthesizes macro signals from price action.
    """
    
    def __init__(self):
        self.name = "Macro Economic Indicator"
        self.version = "1.0.0"
        self.category = "Master Indicators"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Macro Economic metrics
        
        Parameters:
        - macro_period: Period for macro analysis (default: 89)
        - cycle_period: Period for cycle detection (default: 55)
        - expansion_threshold: Threshold for expansion (default: 0.02)
        """
        macro_period = params.get('macro_period', 89)
        cycle_period = params.get('cycle_period', 55)
        expansion_threshold = params.get('expansion_threshold', 0.02)
        
        returns = data['close'].pct_change()
        
        # 1. Economic Growth Proxy (long-term price trend)
        growth_rate = returns.rolling(window=macro_period).sum()
        
        # 2. Economic Momentum (acceleration of growth)
        growth_momentum = growth_rate.diff(cycle_period)
        
        # 3. Volatility as Uncertainty Proxy
        uncertainty = returns.rolling(window=macro_period).std()
        uncertainty_percentile = uncertainty.rolling(window=macro_period * 2).rank(pct=True)
        
        # 4. Volume as Activity Proxy
        activity_level = data['volume'] / data['volume'].rolling(window=macro_period).mean()
        
        # 5. Economic Cycle Phase (expansion, peak, contraction, trough)
        # Expansion: positive growth + increasing momentum
        expansion = (
            (growth_rate > expansion_threshold) &
            (growth_momentum > 0)
        ).astype(int)
        
        # Contraction: negative growth + decreasing momentum
        contraction = (
            (growth_rate < -expansion_threshold) &
            (growth_momentum < 0)
        ).astype(int)
        
        # Peak: positive growth but decreasing momentum
        peak = (
            (growth_rate > 0) &
            (growth_momentum < 0) &
            (expansion == 0)
        ).astype(int)
        
        # Trough: negative growth but increasing momentum
        trough = (
            (growth_rate < 0) &
            (growth_momentum > 0) &
            (contraction == 0)
        ).astype(int)
        
        # 6. Macro Regime (1=expansion, 2=peak, 3=contraction, 4=trough)
        macro_regime = pd.Series(0, index=data.index)
        macro_regime[expansion == 1] = 1
        macro_regime[peak == 1] = 2
        macro_regime[contraction == 1] = 3
        macro_regime[trough == 1] = 4
        
        # 7. Leading Indicator (predicts future regime)
        leading_indicator = growth_momentum * activity_level
        
        # 8. Optimal Macro Conditions (expansion or trough)
        optimal_conditions = (
            ((macro_regime == 1) | (macro_regime == 4)) &
            (uncertainty_percentile < 0.7)
        ).astype(int)
        
        result = pd.DataFrame({
            'growth_rate': growth_rate,
            'growth_momentum': growth_momentum,
            'uncertainty': uncertainty_percentile,
            'activity_level': activity_level,
            'expansion': expansion,
            'contraction': contraction,
            'peak': peak,
            'trough': trough,
            'macro_regime': macro_regime,
            'leading_indicator': leading_indicator,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            ((result['macro_regime'] == 1) | (result['macro_regime'] == 4)) &
            (result['leading_indicator'] > 0)
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
        signal_strength = abs(result['growth_rate']).clip(0, 1)
        
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
            ((result['macro_regime'] == 1) | (result['macro_regime'] == 4)) &
            (result['leading_indicator'] > 0)
        )
        
        exits = (
            (result['macro_regime'] == 3) |
            (result['peak'] == 1) |
            (result['leading_indicator'] < 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['macro_regime'] == 3] = 'contraction'
        exit_reason[result['peak'] == 1] = 'peak_detected'
        
        signal_strength = abs(result['growth_rate']).clip(0, 1)
        
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
            'macro_growth_rate': result['growth_rate'],
            'macro_momentum': result['growth_momentum'],
            'macro_uncertainty': result['uncertainty'],
            'macro_activity': result['activity_level'],
            'macro_expansion': result['expansion'],
            'macro_contraction': result['contraction'],
            'macro_peak': result['peak'],
            'macro_trough': result['trough'],
            'macro_regime': result['macro_regime'],
            'macro_leading': result['leading_indicator'],
            'macro_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'macro_period': [55, 89, 144],
            'cycle_period': [34, 55, 89],
            'expansion_threshold': [0.01, 0.02, 0.03],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
