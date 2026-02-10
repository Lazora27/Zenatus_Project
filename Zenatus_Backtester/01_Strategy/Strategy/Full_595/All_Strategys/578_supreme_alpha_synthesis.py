"""
578 - Supreme Alpha Synthesis
Ultimate Master Indicator: Synthesizes supreme alpha from all market dimensions
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class SupremeAlphaSynthesis:
    """
    Supreme Alpha Synthesis - Ultimate alpha generation
    
    Features:
    - Multi-source alpha extraction
    - Alpha purity measurement
    - Synthesis quality assessment
    - Alpha persistence tracking
    - Performance prediction
    """
    
    def __init__(self):
        self.name = "Supreme Alpha Synthesis"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate supreme alpha score"""
        
        # Parameters
        alpha_period = params.get('alpha_period', 60)
        synthesis_period = params.get('synthesis_period', 40)
        quality_period = params.get('quality_period', 30)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Multi-Source Alpha Extraction
        returns = close.pct_change()
        
        # Momentum alpha
        momentum = returns.rolling(quality_period).mean() / (returns.rolling(quality_period).std() + 1e-10)
        momentum_alpha = np.tanh(momentum)
        
        # Mean reversion alpha
        price_mean = close.rolling(alpha_period).mean()
        mean_reversion = -(close - price_mean) / (close.rolling(alpha_period).std() + 1e-10)
        mean_reversion_alpha = np.tanh(mean_reversion)
        
        # Trend alpha
        trend_slope = close.rolling(synthesis_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        )
        trend_alpha = np.tanh(trend_slope * 100)
        
        # Volume alpha
        volume_trend = volume.rolling(quality_period).mean() / volume.rolling(alpha_period).mean()
        volume_alpha = np.tanh(volume_trend - 1)
        
        # Volatility alpha
        volatility = returns.rolling(quality_period).std()
        volatility_regime = volatility / volatility.rolling(alpha_period).mean()
        volatility_alpha = -np.tanh(volatility_regime - 1)  # Low vol = positive alpha
        
        # Microstructure alpha
        efficiency = abs(close - close.shift(1)) / ((high - low) + 1e-10)
        microstructure_alpha = efficiency.rolling(quality_period).mean()
        
        # 2. Alpha Purity Measurement
        # Combine alphas with adaptive weighting
        alpha_sources = [momentum_alpha, mean_reversion_alpha, trend_alpha, 
                        volume_alpha, volatility_alpha, microstructure_alpha]
        
        # Calculate correlation matrix (low correlation = high purity)
        alpha_correlations = []
        for i, alpha1 in enumerate(alpha_sources):
            for j, alpha2 in enumerate(alpha_sources):
                if i < j:
                    corr = alpha1.rolling(synthesis_period).corr(alpha2)
                    alpha_correlations.append(abs(corr))
        
        if alpha_correlations:
            avg_correlation = sum(alpha_correlations) / len(alpha_correlations)
            alpha_purity = 1 - avg_correlation
        else:
            alpha_purity = pd.Series(1, index=close.index)
        
        # Information ratio (alpha per unit of risk)
        combined_alpha = sum(alpha_sources) / len(alpha_sources)
        alpha_volatility = combined_alpha.rolling(synthesis_period).std()
        information_ratio = abs(combined_alpha) / (alpha_volatility + 1e-10)
        information_ratio_normalized = np.tanh(information_ratio)
        
        alpha_purity_score = (alpha_purity + information_ratio_normalized) / 2
        
        # 3. Synthesis Quality Assessment
        # Agreement among alpha sources
        alpha_agreement = pd.Series(0.0, index=data.index)
        for alpha in alpha_sources:
            alpha_agreement += (np.sign(alpha) == np.sign(combined_alpha)).astype(float)
        alpha_agreement = alpha_agreement / len(alpha_sources)
        
        # Consistency over time
        alpha_consistency = 1 / (1 + combined_alpha.rolling(synthesis_period).std())
        
        # Predictive power (simulated)
        future_returns = returns.shift(-quality_period)
        prediction_accuracy = (np.sign(combined_alpha.shift(quality_period)) == np.sign(future_returns))
        historical_accuracy = prediction_accuracy.rolling(alpha_period).mean()
        
        synthesis_quality = (
            0.4 * alpha_agreement +
            0.3 * alpha_consistency +
            0.3 * historical_accuracy
        )
        
        # 4. Alpha Persistence Tracking
        # How long does alpha last
        alpha_sign = np.sign(combined_alpha)
        alpha_changes = (alpha_sign != alpha_sign.shift()).astype(int)
        
        persistence_counter = pd.Series(0, index=data.index)
        counter = 0
        for i in range(len(data)):
            if alpha_changes.iloc[i]:
                counter = 0
            else:
                counter += 1
            persistence_counter.iloc[i] = counter
        
        alpha_persistence = persistence_counter / alpha_period
        alpha_persistence = alpha_persistence.clip(0, 1)
        
        # Alpha decay rate
        alpha_magnitude = abs(combined_alpha)
        alpha_decay = alpha_magnitude.diff(quality_period)
        decay_rate = -alpha_decay / (alpha_magnitude + 1e-10)
        alpha_sustainability = 1 / (1 + abs(decay_rate))
        
        persistence_score = (alpha_persistence + alpha_sustainability) / 2
        
        # 5. Performance Prediction
        # Expected alpha realization
        alpha_strength = abs(combined_alpha)
        
        # Sharpe-like ratio
        alpha_mean = combined_alpha.rolling(alpha_period).mean()
        alpha_std = combined_alpha.rolling(alpha_period).std()
        sharpe_ratio = alpha_mean / (alpha_std + 1e-10)
        sharpe_normalized = np.tanh(sharpe_ratio)
        
        # Win rate
        positive_alpha = (combined_alpha > 0).astype(int)
        win_rate = positive_alpha.rolling(alpha_period).mean()
        
        # Expected performance
        performance_prediction = (
            0.4 * alpha_strength +
            0.3 * sharpe_normalized +
            0.3 * win_rate
        )
        
        # 6. Supreme Alpha Score
        supreme_alpha = (
            0.30 * combined_alpha +
            0.25 * alpha_purity_score +
            0.20 * synthesis_quality +
            0.15 * persistence_score +
            0.10 * performance_prediction
        )
        
        # 7. Alpha Grade
        alpha_grade = pd.Series(0, index=data.index)
        alpha_grade[(supreme_alpha > 0.8) & (synthesis_quality > 0.8)] = 5  # Supreme
        alpha_grade[(supreme_alpha > 0.6) & (supreme_alpha <= 0.8)] = 4  # Excellent
        alpha_grade[(supreme_alpha > 0.4) & (supreme_alpha <= 0.6)] = 3  # Good
        alpha_grade[(supreme_alpha > 0.2) & (supreme_alpha <= 0.4)] = 2  # Fair
        alpha_grade[(supreme_alpha > 0) & (supreme_alpha <= 0.2)] = 1  # Weak
        alpha_grade[supreme_alpha <= 0] = 0  # No alpha
        
        result = pd.DataFrame(index=data.index)
        result['supreme_alpha'] = supreme_alpha
        result['combined_alpha'] = combined_alpha
        result['alpha_purity_score'] = alpha_purity_score
        result['synthesis_quality'] = synthesis_quality
        result['persistence_score'] = persistence_score
        result['performance_prediction'] = performance_prediction
        result['alpha_grade'] = alpha_grade
        result['information_ratio'] = information_ratio_normalized
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Supreme alpha with high quality
        entries = (
            (indicator['supreme_alpha'] > 0.7) &
            (indicator['synthesis_quality'] > 0.7) &
            (indicator['alpha_purity_score'] > 0.6) &
            (indicator['alpha_grade'] >= 4)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 200)
        sl_pips = params.get('sl_pips', 75)
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
        
        signal_strength = indicator['supreme_alpha'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on alpha decay"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Supreme alpha
        entries = (
            (indicator['supreme_alpha'] > 0.7) &
            (indicator['synthesis_quality'] > 0.7) &
            (indicator['alpha_purity_score'] > 0.6) &
            (indicator['alpha_grade'] >= 4)
        )
        
        # Exit: Alpha decay or quality loss
        exits = (
            (indicator['supreme_alpha'] < 0.2) |
            (indicator['synthesis_quality'] < 0.3) |
            (indicator['alpha_grade'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['supreme_alpha'] < 0.2)] = 'alpha_decay'
        exit_reason[exits & (indicator['synthesis_quality'] < 0.3)] = 'quality_loss'
        exit_reason[exits & (indicator['alpha_grade'] <= 1)] = 'grade_downgrade'
        
        signal_strength = indicator['supreme_alpha'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extract ML features"""
        
        indicator = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        features['supreme_alpha'] = indicator['supreme_alpha']
        features['combined_alpha'] = indicator['combined_alpha']
        features['alpha_purity_score'] = indicator['alpha_purity_score']
        features['synthesis_quality'] = indicator['synthesis_quality']
        features['persistence_score'] = indicator['persistence_score']
        features['performance_prediction'] = indicator['performance_prediction']
        features['alpha_grade'] = indicator['alpha_grade']
        features['information_ratio'] = indicator['information_ratio']
        
        # Additional features
        features['alpha_momentum'] = indicator['supreme_alpha'].diff(5)
        features['quality_trend'] = indicator['synthesis_quality'].rolling(10).mean()
        features['purity_stability'] = indicator['alpha_purity_score'].rolling(15).std()
        features['persistence_trend'] = indicator['persistence_score'].rolling(20).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'alpha_period': [50, 60, 75, 100, 125],
            'synthesis_period': [30, 40, 50, 60, 75],
            'quality_period': [20, 25, 30, 40, 50],
            'tp_pips': [125, 150, 200, 250, 300],
            'sl_pips': [50, 60, 75, 100, 125]
        }
