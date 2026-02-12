"""
573 - Universal Truth Extractor
Ultimate Master Indicator: Extracts universal market truths from noise and chaos
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class UniversalTruthExtractor:
    """
    Universal Truth Extractor - Separates truth from market noise
    
    Features:
    - Truth signal extraction
    - Noise filtering
    - Reality distortion measurement
    - Truth confidence scoring
    - Universal pattern recognition
    """
    
    def __init__(self):
        self.name = "Universal Truth Extractor"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate universal truth score"""
        
        # Parameters
        truth_period = params.get('truth_period', 89)
        extraction_period = params.get('extraction_period', 34)
        noise_period = params.get('noise_period', 21)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Truth Signal Extraction
        returns = close.pct_change()
        
        # Core truth: Long-term trend
        core_truth = close.rolling(truth_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        )
        core_truth_normalized = np.tanh(core_truth * 100)
        
        # Medium-term truth
        medium_truth = close.rolling(extraction_period).mean()
        medium_truth_signal = (close - medium_truth) / medium_truth
        medium_truth_normalized = np.tanh(medium_truth_signal * 10)
        
        # Short-term truth
        short_truth = returns.rolling(noise_period).mean()
        short_truth_normalized = np.tanh(short_truth * 100)
        
        # Extract universal truth (weighted by reliability)
        truth_signal = (
            0.5 * core_truth_normalized +
            0.3 * medium_truth_normalized +
            0.2 * short_truth_normalized
        )
        
        # 2. Noise Filtering
        # Price noise
        price_noise = returns.rolling(noise_period).std()
        price_signal = abs(returns.rolling(noise_period).mean())
        price_snr = price_signal / (price_noise + 1e-10)
        
        # Volume noise
        volume_returns = volume.pct_change()
        volume_noise = volume_returns.rolling(noise_period).std()
        volume_signal = abs(volume_returns.rolling(noise_period).mean())
        volume_snr = volume_signal / (volume_noise + 1e-10)
        
        # Combined noise level
        noise_level = 1 / (1 + (price_snr + volume_snr) / 2)
        
        # Filtered truth (truth with noise removed)
        filtered_truth = truth_signal * (1 - noise_level)
        
        # 3. Reality Distortion Measurement
        # Measure deviation from fundamental value
        fundamental_value = close.rolling(truth_period).median()
        market_price = close
        
        distortion = (market_price - fundamental_value) / fundamental_value
        distortion_magnitude = abs(distortion)
        
        # Distortion persistence
        distortion_duration = (distortion_magnitude > distortion_magnitude.rolling(truth_period).quantile(0.7)).astype(int)
        distortion_persistence = distortion_duration.rolling(extraction_period).sum() / extraction_period
        
        reality_distortion = distortion_magnitude * distortion_persistence
        
        # 4. Truth Confidence Scoring
        # Confidence from signal clarity
        signal_clarity = 1 - noise_level
        
        # Confidence from consistency
        truth_consistency = 1 / (1 + truth_signal.rolling(extraction_period).std())
        
        # Confidence from validation (multiple timeframes agree)
        tf_agreement = (
            (np.sign(core_truth_normalized) == np.sign(truth_signal)).astype(float) +
            (np.sign(medium_truth_normalized) == np.sign(truth_signal)).astype(float) +
            (np.sign(short_truth_normalized) == np.sign(truth_signal)).astype(float)
        ) / 3
        
        # Confidence from low distortion
        distortion_confidence = 1 - np.tanh(reality_distortion)
        
        truth_confidence = (
            0.30 * signal_clarity +
            0.25 * truth_consistency +
            0.25 * tf_agreement +
            0.20 * distortion_confidence
        )
        
        # 5. Universal Pattern Recognition
        # Detect universal patterns (repeating across scales)
        patterns = []
        
        for scale in [5, 13, 21, 34]:
            if scale <= len(close):
                # Pattern at this scale
                pattern = returns.rolling(scale).apply(
                    lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1] if len(x) > 1 else 0
                )
                patterns.append(pattern)
        
        # Universal pattern (consistent across scales)
        if patterns:
            pattern_agreement = pd.Series(0.0, index=data.index)
            mean_pattern = sum(patterns) / len(patterns)
            
            for pattern in patterns:
                pattern_agreement += (np.sign(pattern) == np.sign(mean_pattern)).astype(float)
            pattern_agreement = pattern_agreement / len(patterns)
            
            universal_pattern = abs(mean_pattern) * pattern_agreement
        else:
            universal_pattern = pd.Series(0, index=close.index)
        
        # 6. Universal Truth Score
        universal_truth = (
            0.35 * filtered_truth +
            0.25 * truth_confidence +
            0.20 * (1 - reality_distortion.clip(0, 1)) +
            0.20 * universal_pattern
        )
        
        # 7. Truth Quality
        # Quality from multiple factors
        extraction_quality = (
            0.4 * signal_clarity +
            0.3 * truth_consistency +
            0.3 * (1 - noise_level)
        )
        
        # 8. Truth Stability
        truth_volatility = universal_truth.rolling(extraction_period).std()
        truth_stability = 1 / (1 + truth_volatility)
        
        result = pd.DataFrame(index=data.index)
        result['universal_truth'] = universal_truth
        result['truth_signal'] = truth_signal
        result['filtered_truth'] = filtered_truth
        result['noise_level'] = noise_level
        result['reality_distortion'] = reality_distortion
        result['truth_confidence'] = truth_confidence
        result['universal_pattern'] = universal_pattern
        result['extraction_quality'] = extraction_quality
        result['truth_stability'] = truth_stability
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong universal truth with high confidence
        entries = (
            (indicator['universal_truth'] > 0.6) &
            (indicator['truth_confidence'] > 0.7) &
            (indicator['extraction_quality'] > 0.6) &
            (indicator['noise_level'] < 0.4)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 150)
        sl_pips = params.get('sl_pips', 60)
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
        
        signal_strength = indicator['universal_truth'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on truth degradation"""
        
        indicator = self.calculate(data, params)
        
        # Entry: Strong universal truth
        entries = (
            (indicator['universal_truth'] > 0.6) &
            (indicator['truth_confidence'] > 0.7) &
            (indicator['extraction_quality'] > 0.6) &
            (indicator['noise_level'] < 0.4)
        )
        
        # Exit: Truth reversal or noise increase
        exits = (
            (indicator['universal_truth'] < 0) |
            (indicator['truth_confidence'] < 0.3) |
            (indicator['noise_level'] > 0.7)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['universal_truth'] < 0)] = 'truth_reversal'
        exit_reason[exits & (indicator['truth_confidence'] < 0.3)] = 'confidence_loss'
        exit_reason[exits & (indicator['noise_level'] > 0.7)] = 'noise_surge'
        
        signal_strength = indicator['universal_truth'].clip(-1, 1)
        
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
        features['universal_truth'] = indicator['universal_truth']
        features['truth_signal'] = indicator['truth_signal']
        features['filtered_truth'] = indicator['filtered_truth']
        features['noise_level'] = indicator['noise_level']
        features['reality_distortion'] = indicator['reality_distortion']
        features['truth_confidence'] = indicator['truth_confidence']
        features['universal_pattern'] = indicator['universal_pattern']
        features['extraction_quality'] = indicator['extraction_quality']
        features['truth_stability'] = indicator['truth_stability']
        
        # Additional features
        features['truth_momentum'] = indicator['universal_truth'].diff(5)
        features['confidence_trend'] = indicator['truth_confidence'].rolling(10).mean()
        features['noise_volatility'] = indicator['noise_level'].rolling(15).std()
        features['distortion_trend'] = indicator['reality_distortion'].rolling(20).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'truth_period': [55, 75, 89, 100, 125],
            'extraction_period': [21, 30, 34, 40, 50],
            'noise_period': [13, 17, 21, 25, 30],
            'tp_pips': [100, 125, 150, 175, 200],
            'sl_pips': [40, 50, 60, 75, 100]
        }
