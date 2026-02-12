"""
506_bifurcation_point_detector.py
==================================
Indicator: Bifurcation Point Detector
Category: Chaos Theory / Critical Transitions
Complexity: Elite

Description:
-----------
Detects bifurcation points where market behavior fundamentally changes. Identifies
critical transitions between different dynamic regimes (trending to ranging,
stable to chaotic). Critical for anticipating major market shifts.

Key Features:
- Bifurcation point detection
- Regime transition identification
- Critical slowing down
- Stability loss warning

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_BifurcationPointDetector:
    """
    Bifurcation Point Detector
    
    Identifies critical transitions in market dynamics.
    """
    
    def __init__(self):
        self.name = "Bifurcation Point Detector"
        self.version = "1.0.0"
        self.category = "Chaos Theory"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Bifurcation Point metrics
        
        Parameters:
        - bifurcation_period: Period for bifurcation analysis (default: 55)
        - transition_period: Period for transition detection (default: 34)
        - stability_period: Period for stability measurement (default: 21)
        """
        bifurcation_period = params.get('bifurcation_period', 55)
        transition_period = params.get('transition_period', 34)
        stability_period = params.get('stability_period', 21)
        
        returns = data['close'].pct_change()
        
        # 1. Critical Slowing Down (increasing autocorrelation before transition)
        autocorr = returns.rolling(window=stability_period).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0
        )
        
        # Increasing autocorr = critical slowing down
        autocorr_trend = autocorr.diff(stability_period)
        critical_slowing = (autocorr_trend > 0).astype(int)
        
        # 2. Variance Increase (flickering before transition)
        variance = returns.rolling(window=stability_period).var()
        variance_trend = variance.diff(stability_period)
        variance_increase = (variance_trend > 0).astype(int)
        
        # 3. Stability Loss Score
        stability_loss = (
            critical_slowing * 0.5 +
            variance_increase * 0.5
        )
        
        # 4. Regime Identification (using volatility and trend)
        volatility = returns.rolling(window=transition_period).std()
        trend_strength = abs(data['close'].rolling(window=transition_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        ))
        
        # Regime: 1=trending, 2=ranging, 3=volatile
        regime = pd.Series(1, index=data.index)
        regime[(volatility > volatility.rolling(window=50).quantile(0.7)) & (trend_strength < trend_strength.rolling(window=50).quantile(0.3))] = 2
        regime[volatility > volatility.rolling(window=50).quantile(0.9)] = 3
        
        # 5. Regime Transition Detection
        regime_transition = (regime != regime.shift(1)).astype(int)
        
        # 6. Bifurcation Score (stability loss + regime transition)
        bifurcation_score = stability_loss * regime_transition
        
        # 7. Bifurcation Point (high score = likely bifurcation)
        bifurcation_point = (
            (bifurcation_score > 0.7) &
            (stability_loss > 0.6) &
            (regime_transition == 1)
        ).astype(int)
        
        # 8. Pre-Bifurcation Warning (early warning system)
        pre_bifurcation = (
            (stability_loss > 0.5) &
            (autocorr_trend > 0) &
            (variance_increase == 1)
        ).astype(int)
        
        # 9. Post-Bifurcation Stability (new regime stabilizing)
        regime_age = pd.Series(0, index=data.index)
        age = 0
        current_regime = regime.iloc[0]
        
        for i in range(len(data)):
            if regime.iloc[i] == current_regime:
                age += 1
            else:
                current_regime = regime.iloc[i]
                age = 1
            regime_age.iloc[i] = age
        
        post_bifurcation_stable = (regime_age > stability_period).astype(int)
        
        # 10. Transition Probability (likelihood of imminent transition)
        transition_probability = stability_loss * (1.0 - post_bifurcation_stable)
        
        result = pd.DataFrame({
            'autocorr': autocorr,
            'critical_slowing': critical_slowing,
            'variance_increase': variance_increase,
            'stability_loss': stability_loss,
            'regime': regime,
            'regime_transition': regime_transition,
            'bifurcation_score': bifurcation_score,
            'bifurcation_point': bifurcation_point,
            'pre_bifurcation': pre_bifurcation,
            'regime_age': regime_age,
            'post_bifurcation_stable': post_bifurcation_stable,
            'transition_probability': transition_probability
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: After bifurcation when new regime stabilizes
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Post-bifurcation stable + trending regime + low transition probability
        entries = (
            (result['post_bifurcation_stable'] == 1) &
            (result['regime'] == 1) &
            (result['transition_probability'] < 0.3) &
            (result['regime_age'] > 5)
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
        
        # Signal strength based on regime stability
        signal_strength = (result['regime_age'] / 50).clip(0, 1)
        
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
        
        Entry: Post-bifurcation stable regime
        Exit: When pre-bifurcation warning or regime transition
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['post_bifurcation_stable'] == 1) &
            (result['regime'] == 1) &
            (result['transition_probability'] < 0.3) &
            (result['regime_age'] > 5)
        )
        
        # Exit: Pre-bifurcation warning or regime transition
        exits = (
            (result['pre_bifurcation'] == 1) |
            (result['regime_transition'] == 1) |
            (result['bifurcation_point'] == 1) |
            (result['transition_probability'] > 0.6)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['pre_bifurcation'] == 1] = 'pre_bifurcation_warning'
        exit_reason[result['regime_transition'] == 1] = 'regime_transition'
        exit_reason[result['bifurcation_point'] == 1] = 'bifurcation_detected'
        
        signal_strength = (result['regime_age'] / 50).clip(0, 1)
        
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
            'bif_autocorr': result['autocorr'],
            'bif_critical_slowing': result['critical_slowing'],
            'bif_variance_increase': result['variance_increase'],
            'bif_stability_loss': result['stability_loss'],
            'bif_regime': result['regime'],
            'bif_regime_transition': result['regime_transition'],
            'bif_score': result['bifurcation_score'],
            'bif_point': result['bifurcation_point'],
            'bif_pre_warning': result['pre_bifurcation'],
            'bif_regime_age': result['regime_age'],
            'bif_post_stable': result['post_bifurcation_stable'],
            'bif_transition_prob': result['transition_probability']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'bifurcation_period': [34, 55, 89],
            'transition_period': [21, 34, 55],
            'stability_period': [13, 21, 34],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
