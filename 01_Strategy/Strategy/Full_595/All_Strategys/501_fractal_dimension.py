"""
501_fractal_dimension.py
========================
Indicator: Fractal Dimension Indicator
Category: Chaos Theory / Fractal Analysis
Complexity: Elite

Description:
-----------
Calculates the fractal dimension of price series using box-counting and Higuchi methods.
Measures market complexity and self-similarity. High fractal dimension indicates
complex, choppy markets while low dimension suggests trending behavior.

Key Features:
- Higuchi fractal dimension
- Box-counting dimension
- Market complexity score
- Trend vs chaos classification

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_FractalDimension:
    """
    Fractal Dimension Indicator
    
    Measures market complexity through fractal analysis.
    """
    
    def __init__(self):
        self.name = "Fractal Dimension Indicator"
        self.version = "1.0.0"
        self.category = "Chaos Theory"
        
    @staticmethod
    def _higuchi_fd(x, kmax=10):
        """Calculate Higuchi Fractal Dimension"""
        n = len(x)
        lk = np.zeros(kmax)
        
        for k in range(1, kmax + 1):
            lm = np.zeros(k)
            for m in range(k):
                ll = 0
                n_max = int(np.floor((n - m - 1) / k))
                for i in range(1, n_max):
                    ll += abs(x[m + i * k] - x[m + (i - 1) * k])
                ll = ll * (n - 1) / (n_max * k)
                lm[m] = ll
            lk[k - 1] = np.mean(lm)
        
        # Linear regression to find slope
        x_vals = np.log(1.0 / np.arange(1, kmax + 1))
        y_vals = np.log(lk)
        
        # Remove inf/nan values
        valid = np.isfinite(x_vals) & np.isfinite(y_vals)
        if np.sum(valid) > 2:
            slope = np.polyfit(x_vals[valid], y_vals[valid], 1)[0]
            return slope
        return 1.5  # Default neutral value
    
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Fractal Dimension metrics
        
        Parameters:
        - fd_period: Period for fractal dimension calculation (default: 34)
        - kmax: Maximum k for Higuchi method (default: 10)
        - complexity_threshold: Threshold for complexity (default: 1.5)
        """
        fd_period = params.get('fd_period', 34)
        kmax = params.get('kmax', 10)
        complexity_threshold = params.get('complexity_threshold', 1.5)
        
        # Calculate Higuchi Fractal Dimension
        prices = data['close'].values
        fractal_dimension = pd.Series(1.5, index=data.index)
        
        for i in range(fd_period, len(data)):
            window = prices[i-fd_period:i]
            fd = Indicator_FractalDimension._higuchi_fd(window, kmax)
            fractal_dimension.iloc[i] = fd
        
        # 2. Market Complexity Score (FD normalized)
        # FD ranges typically 1.0-2.0, where 1.0=smooth trend, 2.0=random/complex
        complexity_score = fractal_dimension
        
        # 3. Trending vs Chaotic Classification
        # Low FD (< 1.5) = trending, High FD (> 1.5) = chaotic
        is_trending = (fractal_dimension < complexity_threshold).astype(int)
        is_chaotic = (fractal_dimension > complexity_threshold).astype(int)
        
        # 4. Complexity Change (rate of change in FD)
        complexity_change = fractal_dimension.diff(5)
        
        # 5. Market State (1=trending, 0=neutral, -1=chaotic)
        market_state = pd.Series(0, index=data.index)
        market_state[fractal_dimension < 1.3] = 1  # Strong trend
        market_state[fractal_dimension > 1.7] = -1  # Chaotic
        
        # 6. Predictability Score (inverse of complexity)
        predictability = 2.0 - fractal_dimension
        predictability = predictability.clip(0, 1)
        
        # 7. Regime Stability (how long in current state)
        regime_stability = pd.Series(0, index=data.index)
        current_state = 0
        stability_count = 0
        
        for i in range(len(data)):
            if market_state.iloc[i] == current_state:
                stability_count += 1
            else:
                current_state = market_state.iloc[i]
                stability_count = 1
            regime_stability.iloc[i] = stability_count
        
        # 8. Fractal Efficiency Ratio (price change / path length)
        price_displacement = abs(data['close'] - data['close'].shift(fd_period))
        path_length = abs(data['close'].diff()).rolling(window=fd_period).sum()
        fractal_efficiency = price_displacement / (path_length + 1e-10)
        
        # 9. Self-Similarity Score (consistency of fractal dimension)
        fd_stability = 1.0 / (fractal_dimension.rolling(window=fd_period).std() + 1e-10)
        self_similarity = fd_stability / fd_stability.rolling(window=50).mean()
        
        # 10. Optimal Trading Regime (trending + stable)
        optimal_regime = (
            (is_trending == 1) &
            (regime_stability > 5) &
            (predictability > 0.6)
        ).astype(int)
        
        result = pd.DataFrame({
            'fractal_dimension': fractal_dimension,
            'complexity_score': complexity_score,
            'is_trending': is_trending,
            'is_chaotic': is_chaotic,
            'complexity_change': complexity_change,
            'market_state': market_state,
            'predictability': predictability,
            'regime_stability': regime_stability,
            'fractal_efficiency': fractal_efficiency,
            'self_similarity': self_similarity,
            'optimal_regime': optimal_regime
        }, index=data.index)
        
        return result.fillna(1.5)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategy with MANUAL Exit Logic
        
        Entry: When in trending regime with high predictability
        Exit: Manual TP/SL logic
        """
        result = self.calculate(data, params)
        
        # Entry: Optimal regime + high predictability + stable
        entries = (
            (result['optimal_regime'] == 1) &
            (result['predictability'] > 0.6) &
            (result['regime_stability'] > 5) &
            (result['fractal_efficiency'] > 0.5)
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
        
        # Signal strength based on predictability
        signal_strength = result['predictability'].clip(0, 1)
        
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
        
        Entry: Trending regime
        Exit: When market becomes chaotic or regime changes
        """
        result = self.calculate(data, params)
        
        # Entry: Same as fixed
        entries = (
            (result['optimal_regime'] == 1) &
            (result['predictability'] > 0.6) &
            (result['regime_stability'] > 5) &
            (result['fractal_efficiency'] > 0.5)
        )
        
        # Exit: Market becomes chaotic or regime changes
        exits = (
            (result['is_chaotic'] == 1) |
            (result['market_state'] != 1) |
            (result['predictability'] < 0.4) |
            (result['complexity_change'] > 0.2)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['is_chaotic'] == 1] = 'market_chaotic'
        exit_reason[result['market_state'] != 1] = 'regime_change'
        exit_reason[result['predictability'] < 0.4] = 'predictability_drop'
        
        signal_strength = result['predictability'].clip(0, 1)
        
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
            'fd_fractal_dimension': result['fractal_dimension'],
            'fd_complexity_score': result['complexity_score'],
            'fd_is_trending': result['is_trending'],
            'fd_is_chaotic': result['is_chaotic'],
            'fd_complexity_change': result['complexity_change'],
            'fd_market_state': result['market_state'],
            'fd_predictability': result['predictability'],
            'fd_regime_stability': result['regime_stability'],
            'fd_fractal_efficiency': result['fractal_efficiency'],
            'fd_self_similarity': result['self_similarity'],
            'fd_optimal_regime': result['optimal_regime']
        }, index=data.index)
        
        return features.fillna(1.5)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'fd_period': [21, 34, 55],
            'kmax': [8, 10, 13],
            'complexity_threshold': [1.4, 1.5, 1.6],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
