"""
499_execution_alpha_generator.py
=================================
Indicator: Execution Alpha Generator
Category: Market Microstructure / Alpha Generation
Complexity: Elite

Description:
-----------
Generates alpha specifically from execution timing and microstructure inefficiencies.
Identifies optimal execution windows, cost savings opportunities, and timing-based
edge. Combines execution quality, timing, and market conditions.

Key Features:
- Execution timing alpha
- Cost-based alpha generation
- Timing edge detection
- Execution opportunity scoring

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_ExecutionAlphaGenerator:
    """
    Execution Alpha Generator
    
    Generates alpha from execution timing and microstructure.
    """
    
    def __init__(self):
        self.name = "Execution Alpha Generator"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Execution Alpha metrics
        
        Parameters:
        - alpha_period: Period for alpha calculation (default: 21)
        - timing_period: Period for timing analysis (default: 13)
        - cost_period: Period for cost analysis (default: 8)
        """
        alpha_period = params.get('alpha_period', 21)
        timing_period = params.get('timing_period', 13)
        cost_period = params.get('cost_period', 8)
        
        # 1. Execution Cost Alpha (save on costs)
        spread_proxy = (data['high'] - data['low']) / data['close']
        volatility = data['close'].pct_change().rolling(window=cost_period).std()
        execution_cost = spread_proxy + (2 * volatility)
        
        # Alpha from low-cost periods
        avg_cost = execution_cost.rolling(window=alpha_period).mean()
        cost_alpha = (avg_cost - execution_cost) / (avg_cost + 1e-10)
        
        # 2. Timing Alpha (execute when conditions favorable)
        liquidity_score = data['volume'] / (spread_proxy + 1e-10)
        liquidity_percentile = liquidity_score.rolling(window=timing_period).rank(pct=True)
        
        timing_alpha = liquidity_percentile - 0.5  # -0.5 to +0.5
        
        # 3. Impact Alpha (minimize price impact)
        price_impact = abs(data['close'].pct_change()) / (data['volume'] / data['volume'].rolling(window=alpha_period).mean() + 1e-10)
        avg_impact = price_impact.rolling(window=alpha_period).mean()
        
        impact_alpha = (avg_impact - price_impact) / (avg_impact + 1e-10)
        
        # 4. Slippage Alpha (avoid high slippage periods)
        atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
        slippage_proxy = atr / (data['close'] + 1e-10)
        avg_slippage = slippage_proxy.rolling(window=alpha_period).mean()
        
        slippage_alpha = (avg_slippage - slippage_proxy) / (avg_slippage + 1e-10)
        
        # 5. Composite Execution Alpha
        execution_alpha = (
            cost_alpha * 0.30 +
            timing_alpha * 0.25 +
            impact_alpha * 0.25 +
            slippage_alpha * 0.20
        )
        
        # 6. Alpha Quality (consistency)
        alpha_quality = (execution_alpha > 0).rolling(window=timing_period).mean()
        
        # 7. High-Quality Alpha Signals
        high_quality_alpha = (
            (execution_alpha > 0.3) &
            (alpha_quality > 0.6)
        ).astype(int)
        
        # 8. Alpha Momentum (acceleration)
        alpha_momentum = execution_alpha.diff(cost_period)
        
        # 9. Opportunity Window (optimal execution timing)
        opportunity_window = (
            (cost_alpha > 0.2) &
            (timing_alpha > 0.1) &
            (impact_alpha > 0.1)
        ).astype(int)
        
        # 10. Expected Cost Savings (in basis points)
        cost_savings_bps = cost_alpha * 10000  # Convert to basis points
        
        # 11. Risk-Adjusted Alpha (alpha / volatility)
        risk_adjusted_alpha = execution_alpha / (volatility + 1e-10)
        
        # 12. Alpha Persistence (how long alpha lasts)
        alpha_persistence = pd.Series(0, index=data.index)
        persistence_count = 0
        
        for i in range(len(data)):
            if execution_alpha.iloc[i] > 0:
                persistence_count += 1
            else:
                persistence_count = 0
            alpha_persistence.iloc[i] = persistence_count
        
        result = pd.DataFrame({
            'cost_alpha': cost_alpha,
            'timing_alpha': timing_alpha,
            'impact_alpha': impact_alpha,
            'slippage_alpha': slippage_alpha,
            'execution_alpha': execution_alpha,
            'alpha_quality': alpha_quality,
            'high_quality_alpha': high_quality_alpha,
            'alpha_momentum': alpha_momentum,
            'opportunity_window': opportunity_window,
            'cost_savings_bps': cost_savings_bps,
            'risk_adjusted_alpha': risk_adjusted_alpha,
            'alpha_persistence': alpha_persistence
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When high-quality execution alpha detected
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: High-quality alpha + opportunity window + positive momentum
        entries = (
            (result['high_quality_alpha'] == 1) &
            (result['opportunity_window'] == 1) &
            (result['alpha_momentum'] > 0) &
            (result['execution_alpha'] > 0.3) &
            (result['alpha_persistence'] > 2)
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
        
        # Signal strength based on execution alpha
        signal_strength = (result['execution_alpha'] * 2.0).clip(0, 1)
        
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
        
        Entry: High-quality execution alpha
        Exit: When alpha deteriorates or window closes
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['high_quality_alpha'] == 1) &
            (result['opportunity_window'] == 1) &
            (result['alpha_momentum'] > 0) &
            (result['execution_alpha'] > 0.3) &
            (result['alpha_persistence'] > 2)
        )
        
        # Exit: Alpha turns negative or quality drops
        exits = (
            (result['execution_alpha'] < 0) |
            (result['opportunity_window'] == 0) |
            (result['alpha_quality'] < 0.4) |
            (result['alpha_momentum'] < -0.1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['execution_alpha'] < 0] = 'alpha_negative'
        exit_reason[result['opportunity_window'] == 0] = 'window_closed'
        exit_reason[result['alpha_quality'] < 0.4] = 'quality_drop'
        
        signal_strength = (result['execution_alpha'] * 2.0).clip(0, 1)
        
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
            'eag_cost_alpha': result['cost_alpha'],
            'eag_timing_alpha': result['timing_alpha'],
            'eag_impact_alpha': result['impact_alpha'],
            'eag_slippage_alpha': result['slippage_alpha'],
            'eag_execution_alpha': result['execution_alpha'],
            'eag_alpha_quality': result['alpha_quality'],
            'eag_high_quality_alpha': result['high_quality_alpha'],
            'eag_alpha_momentum': result['alpha_momentum'],
            'eag_opportunity_window': result['opportunity_window'],
            'eag_cost_savings_bps': result['cost_savings_bps'],
            'eag_risk_adjusted_alpha': result['risk_adjusted_alpha'],
            'eag_alpha_persistence': result['alpha_persistence']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'alpha_period': [13, 21, 34],
            'timing_period': [8, 13, 21],
            'cost_period': [5, 8, 13],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
