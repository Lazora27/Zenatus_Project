"""
480_venue_toxicity.py
=====================
Indicator: Venue Toxicity Indicator
Category: Market Microstructure / Venue Analysis
Complexity: Advanced

Description:
-----------
Measures the toxicity level of different trading venues or market conditions.
Identifies periods of adverse selection, information asymmetry, and toxic order flow
that can harm market makers and liquidity providers.

Key Features:
- Venue toxicity score
- Adverse selection rate
- Information asymmetry index
- Toxic flow detection

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_VenueToxicity:
    """
    Venue Toxicity Indicator
    
    Measures market toxicity and adverse selection risk.
    """
    
    def __init__(self):
        self.name = "Venue Toxicity Indicator"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Venue Toxicity metrics
        
        Parameters:
        - toxicity_period: Period for toxicity calculation (default: 21)
        - adverse_period: Period for adverse selection (default: 13)
        - flow_period: Period for flow analysis (default: 8)
        """
        toxicity_period = params.get('toxicity_period', 21)
        adverse_period = params.get('adverse_period', 13)
        flow_period = params.get('flow_period', 8)
        
        # 1. Adverse Selection Rate (price moves against market makers)
        # Proxy: Percentage of trades where price continues in same direction
        price_change = data['close'].diff()
        future_price_change = data['close'].shift(-1).diff()
        adverse_selection = ((price_change * future_price_change) > 0).astype(int)
        adverse_selection_rate = adverse_selection.rolling(window=adverse_period).mean()
        
        # 2. Price Impact Asymmetry (buys impact more than sells = toxic)
        volume_signed = data['volume'] * np.sign(price_change)
        buy_volume = volume_signed.where(volume_signed > 0, 0)
        sell_volume = abs(volume_signed.where(volume_signed < 0, 0))
        
        buy_impact = price_change.where(price_change > 0, 0).rolling(window=flow_period).sum() / \
                     (buy_volume.rolling(window=flow_period).sum() + 1e-10)
        sell_impact = abs(price_change.where(price_change < 0, 0).rolling(window=flow_period).sum()) / \
                      (sell_volume.rolling(window=flow_period).sum() + 1e-10)
        
        impact_asymmetry = abs(buy_impact - sell_impact) / (buy_impact + sell_impact + 1e-10)
        
        # 3. Information Asymmetry Index (volatility after trades)
        post_trade_volatility = data['close'].pct_change().shift(-flow_period).rolling(window=flow_period).std()
        pre_trade_volatility = data['close'].pct_change().rolling(window=flow_period).std()
        information_asymmetry = post_trade_volatility / (pre_trade_volatility + 1e-10)
        
        # 4. Toxic Flow Score (VPIN-like metric)
        volume_imbalance = abs(buy_volume - sell_volume) / (data['volume'] + 1e-10)
        toxic_flow_score = volume_imbalance.rolling(window=flow_period).mean()
        
        # 5. Quote Instability (rapid quote changes = toxic environment)
        quote_changes = (data['high'] - data['low']).pct_change().abs()
        quote_instability = quote_changes.rolling(window=adverse_period).mean()
        
        # 6. Venue Toxicity Composite Score
        toxicity_score = (
            adverse_selection_rate * 0.3 +
            impact_asymmetry * 0.2 +
            information_asymmetry * 0.2 +
            toxic_flow_score * 0.2 +
            quote_instability * 0.1
        )
        
        # Normalize toxicity score
        toxicity_normalized = toxicity_score / (toxicity_score.rolling(window=50).mean() + 1e-10)
        
        # 7. Toxic Events (extreme toxicity periods)
        toxic_events = (toxicity_normalized > 1.5).astype(int)
        
        # 8. Market Maker Profitability (inverse of toxicity)
        mm_profitability = 1.0 / (toxicity_normalized + 1e-10)
        
        # 9. Safe Trading Windows (low toxicity periods)
        safe_windows = (toxicity_normalized < 0.8).astype(int)
        
        # 10. Toxicity Trend (increasing = deteriorating conditions)
        toxicity_trend = toxicity_normalized.diff(flow_period)
        
        result = pd.DataFrame({
            'adverse_selection_rate': adverse_selection_rate,
            'impact_asymmetry': impact_asymmetry,
            'information_asymmetry': information_asymmetry,
            'toxic_flow_score': toxic_flow_score,
            'quote_instability': quote_instability,
            'toxicity_score': toxicity_score,
            'toxicity_normalized': toxicity_normalized,
            'toxic_events': toxic_events,
            'mm_profitability': mm_profitability,
            'safe_windows': safe_windows,
            'toxicity_trend': toxicity_trend
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When toxicity is low (safe trading conditions)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Safe trading window + low toxicity + positive MM profitability
        entries = (
            (result['safe_windows'] == 1) &
            (result['toxicity_normalized'] < 0.7) &
            (result['mm_profitability'] > 1.3) &
            (result['toxicity_trend'] < 0)  # Toxicity decreasing
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
        
        # Signal strength based on inverse toxicity
        signal_strength = result['mm_profitability'] / 3.0
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
        
        Entry: Low toxicity conditions
        Exit: When toxicity spikes or safe window closes
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['safe_windows'] == 1) &
            (result['toxicity_normalized'] < 0.7) &
            (result['mm_profitability'] > 1.3) &
            (result['toxicity_trend'] < 0)
        )
        
        # Exit: Toxicity spike or safe window closes
        exits = (
            (result['safe_windows'] == 0) |
            (result['toxic_events'] == 1) |
            (result['toxicity_trend'] > 0.1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['safe_windows'] == 0] = 'safe_window_closed'
        exit_reason[result['toxic_events'] == 1] = 'toxic_event'
        exit_reason[result['toxicity_trend'] > 0.1] = 'toxicity_increasing'
        
        signal_strength = result['mm_profitability'] / 3.0
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
        
        Returns 11 features for machine learning models
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'venue_adverse_selection': result['adverse_selection_rate'],
            'venue_impact_asymmetry': result['impact_asymmetry'],
            'venue_information_asymmetry': result['information_asymmetry'],
            'venue_toxic_flow': result['toxic_flow_score'],
            'venue_quote_instability': result['quote_instability'],
            'venue_toxicity_score': result['toxicity_score'],
            'venue_toxicity_normalized': result['toxicity_normalized'],
            'venue_toxic_events': result['toxic_events'],
            'venue_mm_profitability': result['mm_profitability'],
            'venue_safe_windows': result['safe_windows'],
            'venue_toxicity_trend': result['toxicity_trend']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'toxicity_period': [13, 21, 34],
            'adverse_period': [8, 13, 21],
            'flow_period': [5, 8, 13],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
