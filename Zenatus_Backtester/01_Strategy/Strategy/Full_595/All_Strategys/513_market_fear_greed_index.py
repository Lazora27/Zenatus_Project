"""
513_market_fear_greed_index.py
===============================
Indicator: Market Fear & Greed Index
Category: Alternative Data / Sentiment Analysis
Complexity: Elite

Description:
-----------
Comprehensive fear and greed index combining volatility, momentum, volume,
and price strength. Identifies extreme fear (buying opportunity) and extreme
greed (selling opportunity). Critical for contrarian trading strategies.

Key Features:
- Fear/greed score calculation
- Extreme emotion detection
- Contrarian opportunity identification
- Emotion regime classification

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MarketFearGreedIndex:
    """
    Market Fear & Greed Index
    
    Measures market emotions for contrarian opportunities.
    """
    
    def __init__(self):
        self.name = "Market Fear & Greed Index"
        self.version = "1.0.0"
        self.category = "Alternative Data"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Fear & Greed Index metrics
        
        Parameters:
        - index_period: Period for index calculation (default: 21)
        - extreme_threshold: Threshold for extreme emotions (default: 75)
        - momentum_period: Period for momentum (default: 13)
        """
        index_period = params.get('index_period', 21)
        extreme_threshold = params.get('extreme_threshold', 75)
        momentum_period = params.get('momentum_period', 13)
        
        # === COMPONENT 1: Price Momentum (25%) ===
        price_momentum = data['close'].pct_change(momentum_period)
        momentum_percentile = price_momentum.rolling(window=index_period * 2).rank(pct=True) * 100
        
        # === COMPONENT 2: Volatility (25%) ===
        volatility = data['close'].pct_change().rolling(window=index_period).std()
        volatility_percentile = volatility.rolling(window=index_period * 2).rank(pct=True) * 100
        # Invert: High volatility = fear (low score)
        volatility_score = 100 - volatility_percentile
        
        # === COMPONENT 3: Volume (20%) ===
        volume_ratio = data['volume'] / data['volume'].rolling(window=index_period).mean()
        volume_percentile = volume_ratio.rolling(window=index_period * 2).rank(pct=True) * 100
        
        # === COMPONENT 4: Market Strength (15%) ===
        # Number of advancing periods
        advancing = (data['close'] > data['close'].shift(1)).astype(int)
        market_strength = advancing.rolling(window=index_period).mean() * 100
        
        # === COMPONENT 5: Price Breadth (15%) ===
        # Distance from moving average
        sma = data['close'].rolling(window=index_period).mean()
        price_breadth = ((data['close'] - sma) / (sma + 1e-10)) * 100
        price_breadth_normalized = (price_breadth + 10).clip(0, 20) / 20 * 100
        
        # === FEAR & GREED INDEX (0-100) ===
        fear_greed_index = (
            momentum_percentile * 0.25 +
            volatility_score * 0.25 +
            volume_percentile * 0.20 +
            market_strength * 0.15 +
            price_breadth_normalized * 0.15
        )
        
        # 6. Emotion Classification (0-25=Fear, 25-45=Fear, 45-55=Neutral, 55-75=Greed, 75-100=Extreme Greed)
        emotion_class = pd.Series(0, index=data.index)
        emotion_class[fear_greed_index < 25] = -2  # Extreme Fear
        emotion_class[(fear_greed_index >= 25) & (fear_greed_index < 45)] = -1  # Fear
        emotion_class[(fear_greed_index >= 45) & (fear_greed_index < 55)] = 0  # Neutral
        emotion_class[(fear_greed_index >= 55) & (fear_greed_index < 75)] = 1  # Greed
        emotion_class[fear_greed_index >= 75] = 2  # Extreme Greed
        
        # 7. Extreme Fear (contrarian buy signal)
        extreme_fear = (fear_greed_index < extreme_threshold).astype(int)
        
        # 8. Extreme Greed (contrarian sell signal)
        extreme_greed = (fear_greed_index > (100 - extreme_threshold)).astype(int)
        
        # 9. Emotion Shift (rapid change in sentiment)
        emotion_shift = abs(fear_greed_index.diff(5))
        
        # 10. Contrarian Opportunity Score
        contrarian_buy = extreme_fear * (100 - fear_greed_index) / 100
        contrarian_sell = extreme_greed * fear_greed_index / 100
        
        # 11. Emotion Momentum (rate of change)
        emotion_momentum = fear_greed_index.diff(momentum_period)
        
        # 12. Optimal Contrarian Entry (extreme + momentum reversal)
        optimal_contrarian_buy = (
            (extreme_fear == 1) &
            (emotion_momentum > 0) &
            (emotion_shift > 10)
        ).astype(int)
        
        optimal_contrarian_sell = (
            (extreme_greed == 1) &
            (emotion_momentum < 0) &
            (emotion_shift > 10)
        ).astype(int)
        
        result = pd.DataFrame({
            'fear_greed_index': fear_greed_index,
            'emotion_class': emotion_class,
            'extreme_fear': extreme_fear,
            'extreme_greed': extreme_greed,
            'emotion_shift': emotion_shift,
            'contrarian_buy': contrarian_buy,
            'contrarian_sell': contrarian_sell,
            'emotion_momentum': emotion_momentum,
            'optimal_contrarian_buy': optimal_contrarian_buy,
            'optimal_contrarian_sell': optimal_contrarian_sell,
            'momentum_component': momentum_percentile,
            'volatility_component': volatility_score,
            'volume_component': volume_percentile,
            'strength_component': market_strength
        }, index=data.index)
        
        return result.fillna(50)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal contrarian buy signal (extreme fear)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal contrarian buy + extreme fear + positive momentum
        entries = (
            (result['optimal_contrarian_buy'] == 1) &
            (result['emotion_momentum'] > 0) &
            (result['fear_greed_index'] < 30)
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
        
        # Signal strength based on contrarian score
        signal_strength = result['contrarian_buy'].clip(0, 1)
        
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
        
        Entry: Extreme fear contrarian
        Exit: When greed returns or index normalizes
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_contrarian_buy'] == 1) &
            (result['emotion_momentum'] > 0) &
            (result['fear_greed_index'] < 30)
        )
        
        # Exit: Greed or normalized
        exits = (
            (result['extreme_greed'] == 1) |
            (result['fear_greed_index'] > 55) |
            (result['emotion_class'] >= 1) |
            (result['emotion_momentum'] < -5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['extreme_greed'] == 1] = 'extreme_greed'
        exit_reason[result['fear_greed_index'] > 55] = 'index_normalized'
        exit_reason[result['emotion_class'] >= 1] = 'greed_detected'
        
        signal_strength = result['contrarian_buy'].clip(0, 1)
        
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
            'fg_index': result['fear_greed_index'],
            'fg_emotion_class': result['emotion_class'],
            'fg_extreme_fear': result['extreme_fear'],
            'fg_extreme_greed': result['extreme_greed'],
            'fg_emotion_shift': result['emotion_shift'],
            'fg_contrarian_buy': result['contrarian_buy'],
            'fg_contrarian_sell': result['contrarian_sell'],
            'fg_emotion_momentum': result['emotion_momentum'],
            'fg_optimal_buy': result['optimal_contrarian_buy'],
            'fg_optimal_sell': result['optimal_contrarian_sell'],
            'fg_momentum_comp': result['momentum_component'],
            'fg_volatility_comp': result['volatility_component'],
            'fg_volume_comp': result['volume_component'],
            'fg_strength_comp': result['strength_component']
        }, index=data.index)
        
        return features.fillna(50)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'index_period': [13, 21, 34],
            'extreme_threshold': [20, 25, 30],
            'momentum_period': [8, 13, 21],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
