"""
531_pairs_trading_cointegration.py
===================================
Indicator: Pairs Trading Cointegration
Category: Exotic Strategies / Statistical Arbitrage
Complexity: Elite

Description:
-----------
Implements pairs trading using cointegration analysis. Detects when price
deviates from its historical relationship with itself (different timeframes
as proxy for pairs). Generates mean-reversion signals based on spread analysis.

Key Features:
- Cointegration testing
- Spread calculation
- Z-score analysis
- Mean reversion signals

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_PairsTradingCointegration:
    """
    Pairs Trading Cointegration
    
    Statistical arbitrage using cointegration.
    """
    
    def __init__(self):
        self.name = "Pairs Trading Cointegration"
        self.version = "1.0.0"
        self.category = "Exotic Strategies"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Pairs Trading metrics
        
        Parameters:
        - cointegration_period: Period for cointegration test (default: 55)
        - spread_period: Period for spread calculation (default: 21)
        - entry_threshold: Z-score threshold for entry (default: 2.0)
        """
        cointegration_period = params.get('cointegration_period', 55)
        spread_period = params.get('spread_period', 21)
        entry_threshold = params.get('entry_threshold', 2.0)
        
        # Use different timeframes as proxy for pairs
        # Fast MA as "pair A", Slow MA as "pair B"
        fast_ma = data['close'].rolling(window=13).mean()
        slow_ma = data['close'].rolling(window=34).mean()
        
        # 1. Spread (difference between pairs)
        spread = fast_ma - slow_ma
        
        # 2. Spread Mean and Std
        spread_mean = spread.rolling(window=spread_period).mean()
        spread_std = spread.rolling(window=spread_period).std()
        
        # 3. Z-Score (standardized spread)
        z_score = (spread - spread_mean) / (spread_std + 1e-10)
        
        # 4. Cointegration Strength (inverse of spread volatility)
        # Low volatility = strong cointegration
        cointegration_strength = 1.0 / (spread_std.rolling(window=cointegration_period).std() + 1e-10)
        cointegration_normalized = cointegration_strength / cointegration_strength.rolling(window=50).mean()
        
        # 5. Mean Reversion Signal (extreme z-score)
        oversold = (z_score < -entry_threshold).astype(int)
        overbought = (z_score > entry_threshold).astype(int)
        
        # 6. Spread Momentum (rate of change)
        spread_momentum = spread.diff(spread_period)
        
        # 7. Half-Life (expected time to mean revert)
        # Simplified: based on autocorrelation
        autocorr = spread.rolling(window=spread_period).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0
        )
        half_life = -np.log(2) / (np.log(abs(autocorr) + 1e-10))
        
        # 8. Optimal Entry (oversold + strong cointegration + positive momentum)
        optimal_entry_long = (
            (oversold == 1) &
            (cointegration_normalized > 0.8) &
            (spread_momentum > 0) &
            (half_life < spread_period)
        ).astype(int)
        
        optimal_entry_short = (
            (overbought == 1) &
            (cointegration_normalized > 0.8) &
            (spread_momentum < 0) &
            (half_life < spread_period)
        ).astype(int)
        
        # 9. Spread Regime (1=cointegrated, 0=neutral, -1=diverging)
        spread_regime = pd.Series(0, index=data.index)
        spread_regime[cointegration_normalized > 1.2] = 1
        spread_regime[cointegration_normalized < 0.6] = -1
        
        result = pd.DataFrame({
            'spread': spread,
            'z_score': z_score,
            'cointegration_strength': cointegration_normalized,
            'oversold': oversold,
            'overbought': overbought,
            'spread_momentum': spread_momentum,
            'half_life': half_life,
            'optimal_entry_long': optimal_entry_long,
            'optimal_entry_short': optimal_entry_short,
            'spread_regime': spread_regime
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal long entry (oversold spread)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_entry_long'] == 1) &
            (result['spread_regime'] == 1) &
            (result['z_score'] < -2.0)
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
        
        signal_strength = abs(result['z_score'] / 3.0).clip(0, 1)
        
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
        
        Entry: Optimal long entry
        Exit: When spread mean reverts or cointegration breaks
        """
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_entry_long'] == 1) &
            (result['spread_regime'] == 1) &
            (result['z_score'] < -2.0)
        )
        
        exits = (
            (result['z_score'] > 0) |
            (result['spread_regime'] == -1) |
            (result['overbought'] == 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['z_score'] > 0] = 'mean_reverted'
        exit_reason[result['spread_regime'] == -1] = 'cointegration_broken'
        exit_reason[result['overbought'] == 1] = 'overbought'
        
        signal_strength = abs(result['z_score'] / 3.0).clip(0, 1)
        
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
            'pairs_spread': result['spread'],
            'pairs_z_score': result['z_score'],
            'pairs_cointegration': result['cointegration_strength'],
            'pairs_oversold': result['oversold'],
            'pairs_overbought': result['overbought'],
            'pairs_momentum': result['spread_momentum'],
            'pairs_half_life': result['half_life'],
            'pairs_entry_long': result['optimal_entry_long'],
            'pairs_entry_short': result['optimal_entry_short'],
            'pairs_regime': result['spread_regime']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'cointegration_period': [34, 55, 89],
            'spread_period': [13, 21, 34],
            'entry_threshold': [1.5, 2.0, 2.5],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
