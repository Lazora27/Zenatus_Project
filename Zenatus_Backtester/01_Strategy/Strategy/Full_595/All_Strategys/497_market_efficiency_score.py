"""
497_market_efficiency_score.py
===============================
Indicator: Market Efficiency Score
Category: Market Microstructure / Market Quality
Complexity: Elite

Description:
-----------
Measures overall market efficiency by analyzing price discovery speed, information
incorporation, and arbitrage opportunities. High efficiency indicates fair pricing
and low friction, while low efficiency reveals trading opportunities.

Key Features:
- Price discovery efficiency
- Information incorporation speed
- Arbitrage opportunity detection
- Market friction measurement

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MarketEfficiencyScore:
    """
    Market Efficiency Score Indicator
    
    Measures market efficiency and pricing quality.
    """
    
    def __init__(self):
        self.name = "Market Efficiency Score"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Market Efficiency Score metrics
        
        Parameters:
        - efficiency_period: Period for efficiency analysis (default: 34)
        - discovery_period: Period for price discovery (default: 21)
        - friction_period: Period for friction measurement (default: 13)
        """
        efficiency_period = params.get('efficiency_period', 34)
        discovery_period = params.get('discovery_period', 21)
        friction_period = params.get('friction_period', 13)
        
        # 1. Price Discovery Speed (how quickly price incorporates information)
        # Measure: Autocorrelation of returns (low = efficient)
        returns = data['close'].pct_change()
        autocorr = returns.rolling(window=discovery_period).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0
        )
        
        # Efficiency increases with lower autocorrelation
        discovery_efficiency = 1.0 - abs(autocorr)
        
        # 2. Information Incorporation (variance ratio test)
        # Efficient market: variance ratio ≈ 1
        returns_variance = returns.rolling(window=discovery_period).var()
        returns_variance_long = returns.rolling(window=discovery_period * 2).var()
        variance_ratio = returns_variance_long / (2 * returns_variance + 1e-10)
        
        # Deviation from 1 indicates inefficiency
        information_efficiency = 1.0 - abs(variance_ratio - 1.0)
        
        # 3. Market Friction (transaction costs proxy)
        spread_proxy = (data['high'] - data['low']) / data['close']
        volatility = returns.rolling(window=friction_period).std()
        
        market_friction = spread_proxy + (2 * volatility)
        friction_normalized = market_friction / market_friction.rolling(window=50).mean()
        
        # Low friction = high efficiency
        friction_efficiency = 1.0 / (friction_normalized + 1e-10)
        
        # 4. Arbitrage Opportunity Score (price deviations)
        # Compare to moving average (fair value proxy)
        fair_value = data['close'].rolling(window=efficiency_period).mean()
        price_deviation = abs(data['close'] - fair_value) / (fair_value + 1e-10)
        
        # High deviation = inefficiency = opportunity
        arbitrage_opportunity = price_deviation / (price_deviation.rolling(window=50).mean() + 1e-10)
        
        # 5. Mean Reversion Speed (how quickly prices return to fair value)
        reversion_speed = 1.0 / (price_deviation.rolling(window=discovery_period).mean() + 1e-10)
        reversion_efficiency = reversion_speed / reversion_speed.rolling(window=50).mean()
        
        # 6. Composite Efficiency Score
        efficiency_score = (
            discovery_efficiency * 0.25 +
            information_efficiency * 0.25 +
            friction_efficiency * 0.25 +
            reversion_efficiency * 0.25
        )
        
        # 7. Efficiency Regime (1=efficient, 0=neutral, -1=inefficient)
        efficiency_regime = pd.Series(0, index=data.index)
        efficiency_regime[efficiency_score > 1.2] = 1
        efficiency_regime[efficiency_score < 0.8] = -1
        
        # 8. Inefficiency Opportunities (low efficiency = trading opportunities)
        inefficiency_score = 1.0 / (efficiency_score + 1e-10)
        
        # 9. Market Quality Index
        liquidity_score = data['volume'] / (spread_proxy + 1e-10)
        liquidity_normalized = liquidity_score / liquidity_score.rolling(window=50).mean()
        
        market_quality = efficiency_score * liquidity_normalized
        
        # 10. Efficiency Stability (consistency)
        efficiency_stability = 1.0 / (efficiency_score.rolling(window=efficiency_period).std() + 1e-10)
        efficiency_stability_normalized = efficiency_stability / efficiency_stability.rolling(window=50).mean()
        
        # 11. Optimal Trading Conditions (moderate inefficiency + high liquidity)
        optimal_conditions = (
            (inefficiency_score > 1.2) &
            (inefficiency_score < 2.0) &
            (liquidity_normalized > 1.2)
        ).astype(int)
        
        result = pd.DataFrame({
            'discovery_efficiency': discovery_efficiency,
            'information_efficiency': information_efficiency,
            'friction_efficiency': friction_efficiency,
            'arbitrage_opportunity': arbitrage_opportunity,
            'reversion_efficiency': reversion_efficiency,
            'efficiency_score': efficiency_score,
            'efficiency_regime': efficiency_regime,
            'inefficiency_score': inefficiency_score,
            'market_quality': market_quality,
            'efficiency_stability': efficiency_stability_normalized,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal trading conditions (moderate inefficiency)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions + high arbitrage opportunity + good market quality
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['arbitrage_opportunity'] > 1.3) &
            (result['market_quality'] > 1.2) &
            (result['efficiency_regime'] == -1)
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
        
        # Signal strength based on inefficiency score
        signal_strength = (result['inefficiency_score'] / 3.0).clip(0, 1)
        
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
        
        Entry: Optimal trading conditions
        Exit: When efficiency improves or conditions deteriorate
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['arbitrage_opportunity'] > 1.3) &
            (result['market_quality'] > 1.2) &
            (result['efficiency_regime'] == -1)
        )
        
        # Exit: Efficiency improves or conditions change
        exits = (
            (result['optimal_conditions'] == 0) |
            (result['efficiency_regime'] == 1) |
            (result['arbitrage_opportunity'] < 1.0) |
            (result['market_quality'] < 1.0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['optimal_conditions'] == 0] = 'conditions_changed'
        exit_reason[result['efficiency_regime'] == 1] = 'market_efficient'
        exit_reason[result['arbitrage_opportunity'] < 1.0] = 'opportunity_closed'
        
        signal_strength = (result['inefficiency_score'] / 3.0).clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extract ML features for model training
        
        Returns 11 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'mes_discovery_efficiency': result['discovery_efficiency'],
            'mes_information_efficiency': result['information_efficiency'],
            'mes_friction_efficiency': result['friction_efficiency'],
            'mes_arbitrage_opportunity': result['arbitrage_opportunity'],
            'mes_reversion_efficiency': result['reversion_efficiency'],
            'mes_efficiency_score': result['efficiency_score'],
            'mes_efficiency_regime': result['efficiency_regime'],
            'mes_inefficiency_score': result['inefficiency_score'],
            'mes_market_quality': result['market_quality'],
            'mes_efficiency_stability': result['efficiency_stability'],
            'mes_optimal_conditions': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'efficiency_period': [21, 34, 55],
            'discovery_period': [13, 21, 34],
            'friction_period': [8, 13, 21],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
