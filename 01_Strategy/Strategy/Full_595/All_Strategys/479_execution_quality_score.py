"""
479_execution_quality_score.py
===============================
Indicator: Execution Quality Score
Category: Market Microstructure / Execution Analysis
Complexity: Advanced

Description:
-----------
Comprehensive execution quality assessment combining slippage, price impact,
timing cost, and opportunity cost. Evaluates optimal execution conditions and
identifies favorable entry/exit windows for large orders.

Key Features:
- Execution quality composite score
- Slippage expectation
- Price impact estimation
- Timing cost analysis

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_ExecutionQualityScore:
    """
    Execution Quality Score Indicator
    
    Comprehensive execution quality assessment.
    """
    
    def __init__(self):
        self.name = "Execution Quality Score"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Execution Quality metrics
        
        Parameters:
        - quality_period: Period for quality calculation (default: 21)
        - impact_period: Period for impact estimation (default: 13)
        - slippage_period: Period for slippage analysis (default: 8)
        """
        quality_period = params.get('quality_period', 21)
        impact_period = params.get('impact_period', 13)
        slippage_period = params.get('slippage_period', 8)
        
        # 1. Slippage Expectation (spread + volatility component)
        spread_proxy = (data['high'] - data['low']) / data['close']
        volatility = data['close'].pct_change().rolling(window=slippage_period).std()
        slippage_expectation = spread_proxy + (2 * volatility)
        
        # 2. Price Impact Estimation (volume shock sensitivity)
        volume_shock = data['volume'] / data['volume'].rolling(window=impact_period).mean()
        price_change = abs(data['close'].pct_change())
        price_impact = price_change * volume_shock
        price_impact_avg = price_impact.rolling(window=impact_period).mean()
        
        # 3. Timing Cost (difference between current and VWAP)
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwap = (typical_price * data['volume']).rolling(window=quality_period).sum() / \
               data['volume'].rolling(window=quality_period).sum()
        timing_cost = abs(data['close'] - vwap) / (vwap + 1e-10)
        
        # 4. Opportunity Cost (missed alpha from delayed execution)
        price_momentum = data['close'].pct_change(quality_period)
        opportunity_cost = abs(price_momentum) * timing_cost
        
        # 5. Liquidity Score (inverse of execution difficulty)
        atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
        liquidity_score = data['volume'] / (atr + 1e-10)
        liquidity_score = liquidity_score / liquidity_score.rolling(window=50).mean()
        
        # 6. Market Stability (low volatility = better execution)
        stability_score = 1.0 / (volatility + 1e-10)
        stability_score = stability_score / stability_score.rolling(window=50).mean()
        
        # 7. Execution Quality Composite Score
        # Lower is better for costs, higher is better for liquidity/stability
        cost_component = (slippage_expectation + price_impact_avg + timing_cost + opportunity_cost) / 4
        benefit_component = (liquidity_score + stability_score) / 2
        
        execution_quality = benefit_component / (cost_component + 1e-10)
        execution_quality = execution_quality / execution_quality.rolling(window=50).mean()
        
        # 8. Optimal Execution Windows (high quality periods)
        optimal_window = (execution_quality > 1.3).astype(int)
        
        # 9. Execution Difficulty Index (inverse of quality)
        difficulty_index = 1.0 / (execution_quality + 1e-10)
        
        # 10. Cost Efficiency Ratio
        cost_efficiency = liquidity_score / (slippage_expectation + 1e-10)
        
        result = pd.DataFrame({
            'slippage_expectation': slippage_expectation,
            'price_impact': price_impact_avg,
            'timing_cost': timing_cost,
            'opportunity_cost': opportunity_cost,
            'liquidity_score': liquidity_score,
            'stability_score': stability_score,
            'execution_quality': execution_quality,
            'optimal_window': optimal_window,
            'difficulty_index': difficulty_index,
            'cost_efficiency': cost_efficiency
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When execution quality is optimal (low costs, high liquidity)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal execution window + high liquidity + low slippage
        entries = (
            (result['optimal_window'] == 1) &
            (result['liquidity_score'] > 1.2) &
            (result['slippage_expectation'] < result['slippage_expectation'].rolling(34).quantile(0.3)) &
            (result['stability_score'] > 1.0)
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
        
        # Signal strength based on execution quality
        signal_strength = result['execution_quality'] / 3.0
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
        
        Entry: Optimal execution quality
        Exit: When quality deteriorates or costs spike
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_window'] == 1) &
            (result['liquidity_score'] > 1.2) &
            (result['slippage_expectation'] < result['slippage_expectation'].rolling(34).quantile(0.3)) &
            (result['stability_score'] > 1.0)
        )
        
        # Exit: Quality drops or costs spike
        exits = (
            (result['optimal_window'] == 0) |
            (result['execution_quality'] < 1.0) |
            (result['slippage_expectation'] > result['slippage_expectation'].rolling(34).quantile(0.7))
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['optimal_window'] == 0] = 'window_closed'
        exit_reason[result['execution_quality'] < 1.0] = 'quality_deteriorated'
        exit_reason[result['slippage_expectation'] > result['slippage_expectation'].rolling(34).quantile(0.7)] = 'slippage_spike'
        
        signal_strength = result['execution_quality'] / 3.0
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
        
        Returns 10 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'exec_quality_slippage': result['slippage_expectation'],
            'exec_quality_price_impact': result['price_impact'],
            'exec_quality_timing_cost': result['timing_cost'],
            'exec_quality_opportunity_cost': result['opportunity_cost'],
            'exec_quality_liquidity': result['liquidity_score'],
            'exec_quality_stability': result['stability_score'],
            'exec_quality_score': result['execution_quality'],
            'exec_quality_optimal_window': result['optimal_window'],
            'exec_quality_difficulty': result['difficulty_index'],
            'exec_quality_cost_efficiency': result['cost_efficiency']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'quality_period': [13, 21, 34],
            'impact_period': [8, 13, 21],
            'slippage_period': [5, 8, 13],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
