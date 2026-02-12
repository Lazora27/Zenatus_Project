"""
498_liquidity_cycle_detector.py
================================
Indicator: Liquidity Cycle Detector
Category: Market Microstructure / Cycle Analysis
Complexity: Elite

Description:
-----------
Detects cyclical patterns in market liquidity. Identifies periods of high/low
liquidity, liquidity expansion/contraction cycles, and optimal timing based on
liquidity rhythms. Critical for timing large orders and understanding market phases.

Key Features:
- Liquidity cycle identification
- Cycle phase detection
- Expansion/contraction measurement
- Cycle-based timing signals

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_LiquidityCycleDetector:
    """
    Liquidity Cycle Detector
    
    Identifies cyclical patterns in market liquidity.
    """
    
    def __init__(self):
        self.name = "Liquidity Cycle Detector"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Liquidity Cycle metrics
        
        Parameters:
        - cycle_period: Period for cycle detection (default: 34)
        - phase_period: Period for phase analysis (default: 21)
        - smoothing: Smoothing factor (default: 3)
        """
        cycle_period = params.get('cycle_period', 34)
        phase_period = params.get('phase_period', 21)
        smoothing = params.get('smoothing', 3)
        
        # 1. Liquidity Proxy (Volume / ATR)
        atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
        liquidity = data['volume'] / (atr + 1e-10)
        
        # 2. Detrended Liquidity (remove trend to see cycles)
        liquidity_trend = liquidity.rolling(window=cycle_period).mean()
        liquidity_detrended = liquidity - liquidity_trend
        
        # 3. Liquidity Cycle (using Hilbert Transform approximation)
        # Smooth the detrended signal
        liquidity_smoothed = liquidity_detrended.rolling(window=smoothing).mean()
        
        # 4. Cycle Phase (0-360 degrees approximation)
        # Use arctan of price vs its derivative
        liquidity_derivative = liquidity_smoothed.diff()
        cycle_phase = np.arctan2(liquidity_derivative, liquidity_smoothed) * 180 / np.pi
        cycle_phase = (cycle_phase + 360) % 360  # Normalize to 0-360
        
        # 5. Cycle Amplitude (strength of cycle)
        cycle_amplitude = liquidity_detrended.rolling(window=phase_period).std()
        
        # 6. Liquidity Expansion/Contraction
        liquidity_change = liquidity.pct_change(phase_period)
        expansion = (liquidity_change > 0).astype(int)
        contraction = (liquidity_change < 0).astype(int)
        
        # 7. Cycle Regime (1=expansion, -1=contraction, 0=neutral)
        cycle_regime = pd.Series(0, index=data.index)
        cycle_regime[expansion == 1] = 1
        cycle_regime[contraction == 1] = -1
        
        # 8. High Liquidity Phase (top quartile)
        high_liquidity_phase = (liquidity > liquidity.rolling(window=cycle_period).quantile(0.75)).astype(int)
        
        # 9. Low Liquidity Phase (bottom quartile)
        low_liquidity_phase = (liquidity < liquidity.rolling(window=cycle_period).quantile(0.25)).astype(int)
        
        # 10. Cycle Turning Points (phase transitions)
        phase_change = cycle_phase.diff().abs()
        turning_point = (phase_change > 90).astype(int)  # Major phase shift
        
        # 11. Optimal Execution Phase (high liquidity + expansion)
        optimal_execution_phase = (
            (high_liquidity_phase == 1) &
            (cycle_regime == 1)
        ).astype(int)
        
        # 12. Cycle Strength (consistency of cycle)
        cycle_strength = cycle_amplitude / (liquidity.rolling(window=cycle_period).mean() + 1e-10)
        
        # 13. Liquidity Momentum (rate of liquidity change)
        liquidity_momentum = liquidity.diff(phase_period)
        
        result = pd.DataFrame({
            'liquidity': liquidity,
            'liquidity_trend': liquidity_trend,
            'liquidity_detrended': liquidity_detrended,
            'cycle_phase': cycle_phase,
            'cycle_amplitude': cycle_amplitude,
            'expansion': expansion,
            'contraction': contraction,
            'cycle_regime': cycle_regime,
            'high_liquidity_phase': high_liquidity_phase,
            'low_liquidity_phase': low_liquidity_phase,
            'turning_point': turning_point,
            'optimal_execution_phase': optimal_execution_phase,
            'cycle_strength': cycle_strength,
            'liquidity_momentum': liquidity_momentum
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When in optimal execution phase (high liquidity + expansion)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal execution phase + positive momentum + strong cycle
        entries = (
            (result['optimal_execution_phase'] == 1) &
            (result['liquidity_momentum'] > 0) &
            (result['cycle_strength'] > 0.1) &
            (result['cycle_regime'] == 1)
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
        
        # Signal strength based on cycle strength
        signal_strength = result['cycle_strength'].clip(0, 1)
        
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
        
        Entry: Optimal execution phase
        Exit: When entering contraction or turning point
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_execution_phase'] == 1) &
            (result['liquidity_momentum'] > 0) &
            (result['cycle_strength'] > 0.1) &
            (result['cycle_regime'] == 1)
        )
        
        # Exit: Contraction phase or turning point or low liquidity
        exits = (
            (result['cycle_regime'] == -1) |
            (result['turning_point'] == 1) |
            (result['low_liquidity_phase'] == 1) |
            (result['optimal_execution_phase'] == 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['cycle_regime'] == -1] = 'contraction_phase'
        exit_reason[result['turning_point'] == 1] = 'cycle_turning_point'
        exit_reason[result['low_liquidity_phase'] == 1] = 'low_liquidity'
        
        signal_strength = result['cycle_strength'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 14 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'lc_liquidity': result['liquidity'],
            'lc_liquidity_trend': result['liquidity_trend'],
            'lc_liquidity_detrended': result['liquidity_detrended'],
            'lc_cycle_phase': result['cycle_phase'],
            'lc_cycle_amplitude': result['cycle_amplitude'],
            'lc_expansion': result['expansion'],
            'lc_contraction': result['contraction'],
            'lc_cycle_regime': result['cycle_regime'],
            'lc_high_liquidity_phase': result['high_liquidity_phase'],
            'lc_low_liquidity_phase': result['low_liquidity_phase'],
            'lc_turning_point': result['turning_point'],
            'lc_optimal_execution': result['optimal_execution_phase'],
            'lc_cycle_strength': result['cycle_strength'],
            'lc_liquidity_momentum': result['liquidity_momentum']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'cycle_period': [21, 34, 55],
            'phase_period': [13, 21, 34],
            'smoothing': [2, 3, 5],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
