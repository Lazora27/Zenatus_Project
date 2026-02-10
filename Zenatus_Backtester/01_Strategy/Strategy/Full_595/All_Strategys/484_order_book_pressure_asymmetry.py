"""
484_order_book_pressure_asymmetry.py
=====================================
Indicator: Order Book Pressure Asymmetry
Category: Market Microstructure / Order Book Analysis
Complexity: Advanced

Description:
-----------
Measures asymmetry in order book pressure between bid and ask sides. Detects
imbalances that predict short-term price movements. Analyzes depth, slope,
and pressure dynamics to identify directional bias in limit order book.

Key Features:
- Bid-ask pressure asymmetry
- Order book slope differential
- Pressure momentum
- Imbalance persistence

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_OrderBookPressureAsymmetry:
    """
    Order Book Pressure Asymmetry Indicator
    
    Measures bid-ask pressure imbalances.
    """
    
    def __init__(self):
        self.name = "Order Book Pressure Asymmetry"
        self.version = "1.0.0"
        self.category = "Market Microstructure"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Order Book Pressure Asymmetry metrics
        
        Parameters:
        - pressure_period: Period for pressure analysis (default: 13)
        - asymmetry_period: Period for asymmetry calculation (default: 21)
        - momentum_period: Period for momentum analysis (default: 8)
        """
        pressure_period = params.get('pressure_period', 13)
        asymmetry_period = params.get('asymmetry_period', 21)
        momentum_period = params.get('momentum_period', 8)
        
        # Proxy for order book: Use high/low as bid/ask levels
        # In real implementation, would use actual order book data
        
        # 1. Bid Pressure Proxy (buying interest at lows)
        bid_pressure = data['volume'] * (data['close'] - data['low']) / (data['high'] - data['low'] + 1e-10)
        
        # 2. Ask Pressure Proxy (selling interest at highs)
        ask_pressure = data['volume'] * (data['high'] - data['close']) / (data['high'] - data['low'] + 1e-10)
        
        # 3. Pressure Asymmetry (positive = bid pressure dominates)
        pressure_asymmetry = (bid_pressure - ask_pressure) / (bid_pressure + ask_pressure + 1e-10)
        
        # 4. Smoothed Asymmetry
        asymmetry_smoothed = pressure_asymmetry.rolling(window=pressure_period).mean()
        
        # 5. Asymmetry Strength (absolute value)
        asymmetry_strength = abs(pressure_asymmetry)
        
        # 6. Order Book Slope (rate of pressure change)
        book_slope = pressure_asymmetry.diff(momentum_period)
        
        # 7. Pressure Momentum (acceleration)
        pressure_momentum = book_slope.diff(momentum_period)
        
        # 8. Imbalance Persistence (how long asymmetry lasts)
        imbalance_persistence = pd.Series(0, index=data.index)
        current_sign = 0
        persistence_count = 0
        
        for i in range(len(data)):
            sign = np.sign(pressure_asymmetry.iloc[i])
            if sign == current_sign and sign != 0:
                persistence_count += 1
            else:
                current_sign = sign
                persistence_count = 1
            imbalance_persistence.iloc[i] = persistence_count
        
        # 9. Pressure Divergence (price vs pressure mismatch)
        price_direction = np.sign(data['close'].diff(pressure_period))
        pressure_direction = np.sign(asymmetry_smoothed)
        pressure_divergence = (price_direction != pressure_direction).astype(int)
        
        # 10. Strong Imbalance Events (extreme asymmetry)
        asymmetry_threshold = asymmetry_strength.rolling(window=asymmetry_period).quantile(0.8)
        strong_imbalance = (asymmetry_strength > asymmetry_threshold).astype(int)
        
        # 11. Bid Dominance Score (0-1, higher = more bid pressure)
        bid_dominance = (pressure_asymmetry + 1) / 2  # Normalize to 0-1
        
        # 12. Pressure Stability (low volatility = stable pressure)
        pressure_volatility = pressure_asymmetry.rolling(window=pressure_period).std()
        pressure_stability = 1.0 / (pressure_volatility + 1e-10)
        pressure_stability_normalized = pressure_stability / pressure_stability.rolling(window=50).mean()
        
        result = pd.DataFrame({
            'bid_pressure': bid_pressure,
            'ask_pressure': ask_pressure,
            'pressure_asymmetry': pressure_asymmetry,
            'asymmetry_smoothed': asymmetry_smoothed,
            'asymmetry_strength': asymmetry_strength,
            'book_slope': book_slope,
            'pressure_momentum': pressure_momentum,
            'imbalance_persistence': imbalance_persistence,
            'pressure_divergence': pressure_divergence,
            'strong_imbalance': strong_imbalance,
            'bid_dominance': bid_dominance,
            'pressure_stability': pressure_stability_normalized
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When strong bid pressure asymmetry detected
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Strong bid imbalance + positive momentum + persistence
        entries = (
            (result['strong_imbalance'] == 1) &
            (result['pressure_asymmetry'] > 0.3) &
            (result['pressure_momentum'] > 0) &
            (result['imbalance_persistence'] > 3) &
            (result['bid_dominance'] > 0.6)
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
        
        # Signal strength based on asymmetry strength
        signal_strength = result['asymmetry_strength'].clip(0, 1)
        
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
        
        Entry: Strong pressure asymmetry
        Exit: When asymmetry reverses or weakens
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['strong_imbalance'] == 1) &
            (result['pressure_asymmetry'] > 0.3) &
            (result['pressure_momentum'] > 0) &
            (result['imbalance_persistence'] > 3) &
            (result['bid_dominance'] > 0.6)
        )
        
        # Exit: Asymmetry reverses or weakens significantly
        exits = (
            (result['pressure_asymmetry'] < 0) |
            (result['pressure_momentum'] < -0.1) |
            (result['bid_dominance'] < 0.5) |
            (result['pressure_divergence'] == 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['pressure_asymmetry'] < 0] = 'asymmetry_reversal'
        exit_reason[result['pressure_momentum'] < -0.1] = 'momentum_reversal'
        exit_reason[result['bid_dominance'] < 0.5] = 'dominance_lost'
        exit_reason[result['pressure_divergence'] == 1] = 'price_divergence'
        
        signal_strength = result['asymmetry_strength'].clip(0, 1)
        
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
            'ob_bid_pressure': result['bid_pressure'],
            'ob_ask_pressure': result['ask_pressure'],
            'ob_pressure_asymmetry': result['pressure_asymmetry'],
            'ob_asymmetry_smoothed': result['asymmetry_smoothed'],
            'ob_asymmetry_strength': result['asymmetry_strength'],
            'ob_book_slope': result['book_slope'],
            'ob_pressure_momentum': result['pressure_momentum'],
            'ob_imbalance_persistence': result['imbalance_persistence'],
            'ob_pressure_divergence': result['pressure_divergence'],
            'ob_strong_imbalance': result['strong_imbalance'],
            'ob_bid_dominance': result['bid_dominance'],
            'ob_pressure_stability': result['pressure_stability']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'pressure_period': [8, 13, 21],
            'asymmetry_period': [13, 21, 34],
            'momentum_period': [5, 8, 13],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
