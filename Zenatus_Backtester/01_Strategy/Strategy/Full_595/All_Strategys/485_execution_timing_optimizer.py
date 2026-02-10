"""
485_execution_timing_optimizer.py
==================================
Indicator: Execution Timing Optimizer
Category: Market Microstructure / Execution Optimization
Complexity: Advanced

Description:
-----------
Identifies optimal timing windows for order execution by analyzing market
microstructure conditions, liquidity cycles, and cost patterns. Minimizes
execution costs through intelligent timing of market orders.

Key Features:
- Optimal execution windows
- Cost minimization score
- Liquidity cycle detection
- Timing efficiency index

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_ExecutionTimingOptimizer:
    """
    Execution Timing Optimizer
    
    Identifies optimal timing for order execution.
    """
    
    def __init__(self):
        self.name = "Execution Timing Optimizer"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Execution Timing metrics
        
        Parameters:
        - timing_period: Period for timing analysis (default: 21)
        - cycle_period: Period for cycle detection (default: 34)
        - cost_period: Period for cost analysis (default: 13)
        """
        timing_period = params.get('timing_period', 21)
        cycle_period = params.get('cycle_period', 34)
        cost_period = params.get('cost_period', 13)
        
        # 1. Execution Cost Proxy (spread + volatility)
        spread = (data['high'] - data['low']) / data['close']
        volatility = data['close'].pct_change().rolling(window=cost_period).std()
        execution_cost = spread + (2 * volatility)
        
        # 2. Cost Percentile (lower = better timing)
        cost_percentile = execution_cost.rolling(window=timing_period).rank(pct=True)
        
        # 3. Liquidity Score (volume / ATR)
        atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
        liquidity_score = data['volume'] / (atr + 1e-10)
        liquidity_percentile = liquidity_score.rolling(window=timing_period).rank(pct=True)
        
        # 4. Optimal Timing Score (low cost + high liquidity)
        timing_score = (1.0 - cost_percentile) * liquidity_percentile
        
        # 5. Liquidity Cycle Detection (periodic patterns in liquidity)
        # Use FFT-like approach with rolling correlation
        liquidity_detrended = liquidity_score - liquidity_score.rolling(window=cycle_period).mean()
        cycle_strength = abs(liquidity_detrended).rolling(window=cycle_period).mean()
        
        # 6. Optimal Execution Windows (top quartile timing scores)
        optimal_window = (timing_score > timing_score.rolling(window=timing_period).quantile(0.75)).astype(int)
        
        # 7. Cost Minimization Score (how much cost can be saved)
        avg_cost = execution_cost.rolling(window=timing_period).mean()
        cost_savings = (avg_cost - execution_cost) / (avg_cost + 1e-10)
        
        # 8. Timing Efficiency Index (consistency of good timing)
        timing_efficiency = timing_score.rolling(window=timing_period).mean()
        
        # 9. Market Impact Expectation (expected slippage)
        volume_shock = data['volume'] / data['volume'].rolling(window=cost_period).mean()
        price_impact = abs(data['close'].pct_change()) * volume_shock
        impact_expectation = price_impact.rolling(window=cost_period).mean()
        
        # 10. Execution Urgency Adjustment (higher urgency = accept worse timing)
        # Proxy: Volatility (high vol = more urgent to execute)
        urgency_factor = volatility / volatility.rolling(window=50).mean()
        
        # 11. Risk-Adjusted Timing Score (adjust for urgency)
        risk_adjusted_timing = timing_score / (urgency_factor + 1e-10)
        
        # 12. Window Duration (consecutive optimal bars)
        window_duration = pd.Series(0, index=data.index)
        duration = 0
        
        for i in range(len(data)):
            if optimal_window.iloc[i] == 1:
                duration += 1
            else:
                duration = 0
            window_duration.iloc[i] = duration
        
        result = pd.DataFrame({
            'execution_cost': execution_cost,
            'cost_percentile': cost_percentile,
            'liquidity_score': liquidity_score,
            'liquidity_percentile': liquidity_percentile,
            'timing_score': timing_score,
            'cycle_strength': cycle_strength,
            'optimal_window': optimal_window,
            'cost_savings': cost_savings,
            'timing_efficiency': timing_efficiency,
            'impact_expectation': impact_expectation,
            'urgency_factor': urgency_factor,
            'risk_adjusted_timing': risk_adjusted_timing,
            'window_duration': window_duration
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When in optimal execution window with high timing score
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal window + high timing score + low cost + good liquidity
        entries = (
            (result['optimal_window'] == 1) &
            (result['timing_score'] > 0.7) &
            (result['cost_percentile'] < 0.3) &
            (result['liquidity_percentile'] > 0.7) &
            (result['window_duration'] > 2)
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
        
        # Signal strength based on timing score
        signal_strength = result['timing_score'].clip(0, 1)
        
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
        
        Entry: Optimal execution timing
        Exit: When timing window closes or costs spike
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_window'] == 1) &
            (result['timing_score'] > 0.7) &
            (result['cost_percentile'] < 0.3) &
            (result['liquidity_percentile'] > 0.7) &
            (result['window_duration'] > 2)
        )
        
        # Exit: Window closes or costs deteriorate
        exits = (
            (result['optimal_window'] == 0) |
            (result['timing_score'] < 0.5) |
            (result['cost_percentile'] > 0.7)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['optimal_window'] == 0] = 'window_closed'
        exit_reason[result['timing_score'] < 0.5] = 'timing_deteriorated'
        exit_reason[result['cost_percentile'] > 0.7] = 'costs_increased'
        
        signal_strength = result['timing_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 13 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'exec_timing_cost': result['execution_cost'],
            'exec_timing_cost_percentile': result['cost_percentile'],
            'exec_timing_liquidity': result['liquidity_score'],
            'exec_timing_liquidity_pct': result['liquidity_percentile'],
            'exec_timing_score': result['timing_score'],
            'exec_timing_cycle_strength': result['cycle_strength'],
            'exec_timing_optimal_window': result['optimal_window'],
            'exec_timing_cost_savings': result['cost_savings'],
            'exec_timing_efficiency': result['timing_efficiency'],
            'exec_timing_impact': result['impact_expectation'],
            'exec_timing_urgency': result['urgency_factor'],
            'exec_timing_risk_adjusted': result['risk_adjusted_timing'],
            'exec_timing_window_duration': result['window_duration']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'timing_period': [13, 21, 34],
            'cycle_period': [21, 34, 55],
            'cost_period': [8, 13, 21],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
