"""
511_social_sentiment_analyzer.py
=================================
Indicator: Social Sentiment Analyzer
Category: Alternative Data / Sentiment Analysis
Complexity: Elite

Description:
-----------
Analyzes market sentiment from price action and volume patterns as proxy for
social sentiment. Detects bullish/bearish sentiment shifts, sentiment extremes,
and contrarian opportunities. Uses price behavior to infer market psychology.

Key Features:
- Sentiment score calculation
- Bullish/bearish classification
- Sentiment extremes detection
- Contrarian signals

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_SocialSentimentAnalyzer:
    """
    Social Sentiment Analyzer
    
    Analyzes market sentiment from price action patterns.
    """
    
    def __init__(self):
        self.name = "Social Sentiment Analyzer"
        self.version = "1.0.0"
        self.category = "Alternative Data"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Social Sentiment metrics
        
        Parameters:
        - sentiment_period: Period for sentiment analysis (default: 21)
        - extreme_threshold: Threshold for extreme sentiment (default: 0.8)
        - momentum_period: Period for momentum calculation (default: 13)
        """
        sentiment_period = params.get('sentiment_period', 21)
        extreme_threshold = params.get('extreme_threshold', 0.8)
        momentum_period = params.get('momentum_period', 13)
        
        # 1. Price Momentum Sentiment (positive momentum = bullish sentiment)
        price_momentum = data['close'].pct_change(momentum_period)
        sentiment_from_momentum = np.tanh(price_momentum * 100)  # Normalize to -1 to 1
        
        # 2. Volume Sentiment (high volume on up days = bullish)
        price_change = data['close'].diff()
        volume_sentiment = (
            (price_change > 0).astype(int) * data['volume'] -
            (price_change < 0).astype(int) * data['volume']
        )
        volume_sentiment_normalized = volume_sentiment / data['volume'].rolling(window=sentiment_period).sum()
        
        # 3. Volatility Sentiment (high volatility = fear/uncertainty)
        volatility = data['close'].pct_change().rolling(window=sentiment_period).std()
        volatility_percentile = volatility.rolling(window=sentiment_period * 2).rank(pct=True)
        
        # High volatility = negative sentiment
        volatility_sentiment = 1.0 - (volatility_percentile * 2)  # Convert to -1 to 1
        
        # 4. Trend Sentiment (strong trend = confidence)
        sma_fast = data['close'].rolling(window=momentum_period).mean()
        sma_slow = data['close'].rolling(window=sentiment_period).mean()
        trend_sentiment = (sma_fast - sma_slow) / (sma_slow + 1e-10)
        trend_sentiment = np.tanh(trend_sentiment * 10)
        
        # 5. Composite Sentiment Score
        sentiment_score = (
            sentiment_from_momentum * 0.3 +
            volume_sentiment_normalized * 0.3 +
            volatility_sentiment * 0.2 +
            trend_sentiment * 0.2
        )
        
        # 6. Sentiment Classification (1=bullish, 0=neutral, -1=bearish)
        sentiment_class = pd.Series(0, index=data.index)
        sentiment_class[sentiment_score > 0.3] = 1
        sentiment_class[sentiment_score < -0.3] = -1
        
        # 7. Extreme Sentiment Detection
        sentiment_percentile = sentiment_score.rolling(window=sentiment_period * 2).rank(pct=True)
        
        extreme_bullish = (sentiment_percentile > extreme_threshold).astype(int)
        extreme_bearish = (sentiment_percentile < (1 - extreme_threshold)).astype(int)
        
        # 8. Sentiment Shift (rapid change in sentiment)
        sentiment_shift = abs(sentiment_score.diff(5))
        sentiment_shift_normalized = sentiment_shift / (sentiment_shift.rolling(window=sentiment_period).mean() + 1e-10)
        
        # 9. Contrarian Signal (extreme sentiment = reversal opportunity)
        contrarian_bullish = (extreme_bearish == 1).astype(int)  # Extreme bearish -> buy
        contrarian_bearish = (extreme_bullish == 1).astype(int)  # Extreme bullish -> sell
        
        # 10. Sentiment Momentum (acceleration)
        sentiment_momentum = sentiment_score.diff(momentum_period)
        
        # 11. Sentiment Divergence (sentiment vs price)
        price_direction = np.sign(data['close'].pct_change(sentiment_period))
        sentiment_direction = np.sign(sentiment_score)
        
        sentiment_divergence = (
            (price_direction != sentiment_direction) &
            (abs(sentiment_score) > 0.3)
        ).astype(int)
        
        result = pd.DataFrame({
            'sentiment_score': sentiment_score,
            'sentiment_class': sentiment_class,
            'extreme_bullish': extreme_bullish,
            'extreme_bearish': extreme_bearish,
            'sentiment_shift': sentiment_shift_normalized,
            'contrarian_bullish': contrarian_bullish,
            'contrarian_bearish': contrarian_bearish,
            'sentiment_momentum': sentiment_momentum,
            'sentiment_divergence': sentiment_divergence,
            'momentum_sentiment': sentiment_from_momentum,
            'volume_sentiment': volume_sentiment_normalized,
            'volatility_sentiment': volatility_sentiment,
            'trend_sentiment': trend_sentiment
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When contrarian bullish signal (extreme bearish sentiment)
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Contrarian bullish + positive momentum + sentiment shift
        entries = (
            (result['contrarian_bullish'] == 1) &
            (result['sentiment_momentum'] > 0) &
            (result['sentiment_shift'] > 1.2)
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
        
        # Signal strength based on sentiment shift
        signal_strength = (result['sentiment_shift'] / 3.0).clip(0, 1)
        
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
        
        Entry: Contrarian signal
        Exit: When sentiment normalizes or reverses
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['contrarian_bullish'] == 1) &
            (result['sentiment_momentum'] > 0) &
            (result['sentiment_shift'] > 1.2)
        )
        
        # Exit: Sentiment normalizes or extreme bullish reached
        exits = (
            (result['extreme_bullish'] == 1) |
            (result['sentiment_class'] == 0) |
            (result['sentiment_momentum'] < -0.1) |
            (result['sentiment_divergence'] == 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['extreme_bullish'] == 1] = 'extreme_bullish'
        exit_reason[result['sentiment_class'] == 0] = 'sentiment_normalized'
        exit_reason[result['sentiment_momentum'] < -0.1] = 'momentum_reversal'
        
        signal_strength = (result['sentiment_shift'] / 3.0).clip(0, 1)
        
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
            'sent_score': result['sentiment_score'],
            'sent_class': result['sentiment_class'],
            'sent_extreme_bullish': result['extreme_bullish'],
            'sent_extreme_bearish': result['extreme_bearish'],
            'sent_shift': result['sentiment_shift'],
            'sent_contrarian_bull': result['contrarian_bullish'],
            'sent_contrarian_bear': result['contrarian_bearish'],
            'sent_momentum': result['sentiment_momentum'],
            'sent_divergence': result['sentiment_divergence'],
            'sent_momentum_component': result['momentum_sentiment'],
            'sent_volume_component': result['volume_sentiment'],
            'sent_volatility_component': result['volatility_sentiment'],
            'sent_trend_component': result['trend_sentiment']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'sentiment_period': [13, 21, 34],
            'extreme_threshold': [0.75, 0.80, 0.85],
            'momentum_period': [8, 13, 21],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
