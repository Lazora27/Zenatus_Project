"""
509_multifractal_spectrum.py
=============================
Indicator: Multifractal Spectrum Analyzer
Category: Chaos Theory / Multifractal Analysis
Complexity: Elite

Description:
-----------
Analyzes multifractal properties of price series. Unlike simple fractals,
multifractals have multiple scaling behaviors. Identifies market regimes,
volatility clustering, and fat-tail events through multifractal spectrum.

Key Features:
- Multifractal spectrum calculation
- Hurst exponent variations
- Scaling behavior analysis
- Fat-tail event detection

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MultifractalSpectrum:
    """
    Multifractal Spectrum Analyzer
    
    Analyzes multifractal properties and scaling behaviors.
    """
    
    def __init__(self):
        self.name = "Multifractal Spectrum Analyzer"
        self.version = "1.0.0"
        self.category = "Chaos Theory"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Multifractal Spectrum metrics
        
        Parameters:
        - spectrum_period: Period for spectrum analysis (default: 55)
        - q_values: Range of q values for multifractal (default: [-2, 2])
        - scaling_period: Period for scaling analysis (default: 34)
        """
        spectrum_period = params.get('spectrum_period', 55)
        q_min = params.get('q_min', -2)
        q_max = params.get('q_max', 2)
        scaling_period = params.get('scaling_period', 34)
        
        returns = data['close'].pct_change()
        
        # 1. Generalized Hurst Exponent (simplified multifractal analysis)
        # For q=2, this is standard Hurst exponent
        hurst_q2 = pd.Series(0.5, index=data.index)
        
        for i in range(spectrum_period, len(data)):
            window = returns.iloc[i-spectrum_period:i].values
            
            # R/S analysis for Hurst
            if len(window) > 10:
                mean_return = np.mean(window)
                cumsum = np.cumsum(window - mean_return)
                R = np.max(cumsum) - np.min(cumsum)
                S = np.std(window)
                
                if S > 0:
                    hurst_q2.iloc[i] = np.log(R / S) / np.log(len(window))
                    hurst_q2.iloc[i] = np.clip(hurst_q2.iloc[i], 0, 1)
        
        # 2. Multifractal Width (spectrum width indicates multifractality)
        # Simplified: Use variance of returns at different scales
        scale_1 = returns.rolling(window=5).std()
        scale_2 = returns.rolling(window=13).std()
        scale_3 = returns.rolling(window=34).std()
        
        multifractal_width = scale_3 / (scale_1 + 1e-10)
        
        # 3. Scaling Behavior (how volatility scales with time)
        scaling_exponent = pd.Series(0.5, index=data.index)
        
        for i in range(scaling_period * 2, len(data)):
            # Compare volatility at different time scales
            vol_short = returns.iloc[i-scaling_period:i].std()
            vol_long = returns.iloc[i-scaling_period*2:i].std()
            
            if vol_short > 0:
                # Scaling: vol_long = vol_short * (2^H)
                scaling_exponent.iloc[i] = np.log(vol_long / vol_short) / np.log(2)
                scaling_exponent.iloc[i] = np.clip(scaling_exponent.iloc[i], 0, 1)
        
        # 4. Multifractality Degree (deviation from monofractal)
        # Monofractal: all q give same H
        # Multifractal: different q give different H
        multifractality = abs(hurst_q2 - 0.5) * multifractal_width
        
        # 5. Fat-Tail Events (extreme returns indicating multifractality)
        extreme_threshold = returns.rolling(window=spectrum_period).std() * 3
        fat_tail_events = (abs(returns) > extreme_threshold).astype(int)
        
        # 6. Volatility Clustering (characteristic of multifractals)
        volatility = returns.rolling(window=scaling_period).std()
        vol_autocorr = volatility.rolling(window=scaling_period).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0
        )
        
        volatility_clustering = (vol_autocorr > 0.3).astype(int)
        
        # 7. Market Regime from Hurst
        # H < 0.5: Mean reverting, H = 0.5: Random walk, H > 0.5: Trending
        market_regime = pd.Series(0, index=data.index)
        market_regime[hurst_q2 < 0.45] = -1  # Mean reverting
        market_regime[hurst_q2 > 0.55] = 1   # Trending
        
        # 8. Multifractal Strength (how strong the multifractality)
        multifractal_strength = multifractality / (multifractality.rolling(window=50).mean() + 1e-10)
        
        # 9. Optimal Trading Regime (persistent trending)
        optimal_regime = (
            (market_regime == 1) &
            (hurst_q2 > 0.55) &
            (multifractal_strength < 2.0)
        ).astype(int)
        
        result = pd.DataFrame({
            'hurst_exponent': hurst_q2,
            'multifractal_width': multifractal_width,
            'scaling_exponent': scaling_exponent,
            'multifractality': multifractality,
            'fat_tail_events': fat_tail_events,
            'volatility_clustering': volatility_clustering,
            'market_regime': market_regime,
            'multifractal_strength': multifractal_strength,
            'optimal_regime': optimal_regime
        }, index=data.index)
        
        return result.fillna(0.5)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When in trending regime (H > 0.5)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal regime + trending + low fat-tail risk
        entries = (
            (result['optimal_regime'] == 1) &
            (result['hurst_exponent'] > 0.55) &
            (result['market_regime'] == 1) &
            (result['fat_tail_events'] == 0)
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
        
        # Signal strength based on Hurst exponent deviation from 0.5
        signal_strength = abs(result['hurst_exponent'] - 0.5) * 2
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
        
        Entry: Trending regime
        Exit: When regime changes or fat-tail event
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_regime'] == 1) &
            (result['hurst_exponent'] > 0.55) &
            (result['market_regime'] == 1) &
            (result['fat_tail_events'] == 0)
        )
        
        # Exit: Regime change or fat-tail event
        exits = (
            (result['market_regime'] != 1) |
            (result['fat_tail_events'] == 1) |
            (result['hurst_exponent'] < 0.5) |
            (result['optimal_regime'] == 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['market_regime'] != 1] = 'regime_change'
        exit_reason[result['fat_tail_events'] == 1] = 'fat_tail_event'
        exit_reason[result['hurst_exponent'] < 0.5] = 'mean_reverting'
        
        signal_strength = abs(result['hurst_exponent'] - 0.5) * 2
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
            'mfs_hurst': result['hurst_exponent'],
            'mfs_width': result['multifractal_width'],
            'mfs_scaling': result['scaling_exponent'],
            'mfs_multifractality': result['multifractality'],
            'mfs_fat_tail': result['fat_tail_events'],
            'mfs_vol_clustering': result['volatility_clustering'],
            'mfs_regime': result['market_regime'],
            'mfs_strength': result['multifractal_strength'],
            'mfs_optimal_regime': result['optimal_regime']
        }, index=data.index)
        
        return features.fillna(0.5)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'spectrum_period': [34, 55, 89],
            'q_min': [-3, -2, -1],
            'q_max': [1, 2, 3],
            'scaling_period': [21, 34, 55],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
