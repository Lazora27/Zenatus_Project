"""
514_alternative_data_composite.py
==================================
Indicator: Alternative Data Composite
Category: Alternative Data / Multi-Source Integration
Complexity: Elite

Description:
-----------
Composite indicator integrating multiple alternative data sources proxied through
market behavior. Combines sentiment, news impact, behavioral patterns, and
market microstructure to generate unified alternative data signals.

Key Features:
- Multi-source data integration
- Composite alternative alpha
- Signal quality assessment
- Unified opportunity scoring

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 12+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_AlternativeDataComposite:
    """
    Alternative Data Composite Indicator
    
    Integrates multiple alternative data proxies.
    """
    
    def __init__(self):
        self.name = "Alternative Data Composite"
        self.version = "1.0.0"
        self.category = "Alternative Data"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Alternative Data Composite metrics
        
        Parameters:
        - composite_period: Period for composite analysis (default: 21)
        - quality_period: Period for quality assessment (default: 13)
        - alpha_threshold: Threshold for alpha signals (default: 0.6)
        """
        composite_period = params.get('composite_period', 21)
        quality_period = params.get('quality_period', 13)
        alpha_threshold = params.get('alpha_threshold', 0.6)
        
        returns = data['close'].pct_change()
        
        # === COMPONENT 1: Sentiment Proxy (25%) ===
        price_momentum = data['close'].pct_change(quality_period)
        volume_trend = data['volume'] / data['volume'].rolling(window=composite_period).mean()
        
        sentiment_proxy = np.tanh(price_momentum * 10) * volume_trend
        sentiment_normalized = sentiment_proxy / (abs(sentiment_proxy).rolling(window=50).mean() + 1e-10)
        
        # === COMPONENT 2: News Impact Proxy (20%) ===
        abnormal_returns = abs(returns) / (returns.rolling(window=composite_period).std() + 1e-10)
        volume_spike = data['volume'] / data['volume'].rolling(window=composite_period).mean()
        
        news_impact_proxy = abnormal_returns * volume_spike
        news_normalized = news_impact_proxy / (news_impact_proxy.rolling(window=50).mean() + 1e-10)
        
        # === COMPONENT 3: Behavioral Pattern Proxy (20%) ===
        # Detect herding (high correlation of returns)
        returns_consistency = returns.rolling(window=quality_period).apply(
            lambda x: len(x[x > 0]) / len(x) if len(x) > 0 else 0.5
        )
        
        herding_score = abs(returns_consistency - 0.5) * 2  # 0 to 1
        behavioral_proxy = herding_score * np.sign(returns_consistency - 0.5)
        
        # === COMPONENT 4: Market Microstructure Proxy (20%) ===
        spread_proxy = (data['high'] - data['low']) / data['close']
        liquidity_score = data['volume'] / (spread_proxy + 1e-10)
        
        microstructure_proxy = liquidity_score / liquidity_score.rolling(window=50).mean() - 1.0
        
        # === COMPONENT 5: Volatility Regime Proxy (15%) ===
        volatility = returns.rolling(window=composite_period).std()
        volatility_regime = volatility / volatility.rolling(window=50).mean()
        
        # Prefer moderate volatility
        volatility_proxy = 1.0 - abs(volatility_regime - 1.0)
        
        # === COMPOSITE ALTERNATIVE DATA SCORE ===
        alt_data_score = (
            sentiment_normalized * 0.25 +
            news_normalized * 0.20 +
            behavioral_proxy * 0.20 +
            microstructure_proxy * 0.20 +
            volatility_proxy * 0.15
        )
        
        # 6. Signal Quality (consistency)
        signal_quality = (alt_data_score > 0).rolling(window=quality_period).mean()
        
        # 7. High-Quality Signals
        high_quality_signal = (
            (abs(alt_data_score) > alpha_threshold) &
            (signal_quality > 0.6)
        ).astype(int)
        
        # 8. Alternative Alpha Direction
        alpha_direction = np.sign(alt_data_score)
        
        # 9. Opportunity Rank (percentile)
        opportunity_rank = alt_data_score.rolling(window=composite_period).rank(pct=True)
        
        # 10. Composite Strength
        composite_strength = abs(alt_data_score)
        
        # 11. Multi-Source Confirmation (all components aligned)
        components_aligned = (
            (np.sign(sentiment_normalized) == np.sign(behavioral_proxy)) &
            (np.sign(behavioral_proxy) == np.sign(microstructure_proxy))
        ).astype(int)
        
        # 12. Optimal Entry Conditions
        optimal_entry = (
            (high_quality_signal == 1) &
            (alpha_direction > 0) &
            (opportunity_rank > 0.7) &
            (components_aligned == 1)
        ).astype(int)
        
        result = pd.DataFrame({
            'sentiment_proxy': sentiment_normalized,
            'news_impact_proxy': news_normalized,
            'behavioral_proxy': behavioral_proxy,
            'microstructure_proxy': microstructure_proxy,
            'volatility_proxy': volatility_proxy,
            'alt_data_score': alt_data_score,
            'signal_quality': signal_quality,
            'high_quality_signal': high_quality_signal,
            'alpha_direction': alpha_direction,
            'opportunity_rank': opportunity_rank,
            'composite_strength': composite_strength,
            'components_aligned': components_aligned,
            'optimal_entry': optimal_entry
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When optimal entry conditions met
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal entry + high quality + strong composite
        entries = (
            (result['optimal_entry'] == 1) &
            (result['signal_quality'] > 0.6) &
            (result['composite_strength'] > 0.6) &
            (result['components_aligned'] == 1)
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
        
        # Signal strength based on composite strength
        signal_strength = result['composite_strength'].clip(0, 1)
        
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
        
        Entry: Optimal alternative data signal
        Exit: When signal quality drops or direction reverses
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_entry'] == 1) &
            (result['signal_quality'] > 0.6) &
            (result['composite_strength'] > 0.6) &
            (result['components_aligned'] == 1)
        )
        
        # Exit: Quality drops or direction reverses
        exits = (
            (result['signal_quality'] < 0.4) |
            (result['alpha_direction'] < 0) |
            (result['components_aligned'] == 0) |
            (result['composite_strength'] < 0.3)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['signal_quality'] < 0.4] = 'quality_drop'
        exit_reason[result['alpha_direction'] < 0] = 'direction_reversal'
        exit_reason[result['components_aligned'] == 0] = 'alignment_lost'
        
        signal_strength = result['composite_strength'].clip(0, 1)
        
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
            'alt_sentiment': result['sentiment_proxy'],
            'alt_news_impact': result['news_impact_proxy'],
            'alt_behavioral': result['behavioral_proxy'],
            'alt_microstructure': result['microstructure_proxy'],
            'alt_volatility': result['volatility_proxy'],
            'alt_score': result['alt_data_score'],
            'alt_quality': result['signal_quality'],
            'alt_high_quality': result['high_quality_signal'],
            'alt_direction': result['alpha_direction'],
            'alt_opportunity_rank': result['opportunity_rank'],
            'alt_strength': result['composite_strength'],
            'alt_aligned': result['components_aligned'],
            'alt_optimal_entry': result['optimal_entry']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'composite_period': [13, 21, 34],
            'quality_period': [8, 13, 21],
            'alpha_threshold': [0.5, 0.6, 0.7],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
