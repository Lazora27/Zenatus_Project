"""
586 - Omniversal Intelligence Core
Ultimate Master Indicator: Core intelligence spanning all universes of market behavior
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class OmniversalIntelligenceCore:
    """
    Omniversal Intelligence Core - Universal intelligence system
    
    Features:
    - Multi-universe analysis
    - Core intelligence extraction
    - Universal pattern recognition
    - Omniversal synthesis
    - Intelligence quality
    """
    
    def __init__(self):
        self.name = "Omniversal Intelligence Core"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate omniversal intelligence score"""
        
        # Parameters
        omniversal_period = params.get('omniversal_period', 144)
        intelligence_period = params.get('intelligence_period', 89)
        core_period = params.get('core_period', 55)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Multi-Universe Analysis
        # Universe 1: Trend universe
        trend_strength = close.rolling(intelligence_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        trend_direction = np.sign(close.rolling(intelligence_period).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) > 1 else 0
        ))
        universe_trend = trend_strength * trend_direction
        
        # Universe 2: Momentum universe
        momentum = returns.rolling(core_period).mean() / (returns.rolling(core_period).std() + 1e-10)
        universe_momentum = np.tanh(momentum)
        
        # Universe 3: Volume universe
        volume_profile = volume / volume.rolling(intelligence_period).mean()
        universe_volume = np.tanh(volume_profile - 1)
        
        # Universe 4: Volatility universe
        volatility = returns.rolling(core_period).std()
        volatility_regime = volatility / volatility.rolling(omniversal_period).mean()
        universe_volatility = -np.tanh(volatility_regime - 1)
        
        # Universe 5: Microstructure universe
        efficiency = abs(close - close.shift(1)) / ((high - low) + 1e-10)
        universe_microstructure = efficiency.rolling(core_period).mean()
        
        # 2. Core Intelligence Extraction
        universes = [universe_trend, universe_momentum, universe_volume, 
                    universe_volatility, universe_microstructure]
        
        # Extract core intelligence
        core_intelligence = sum(universes) / len(universes)
        
        # Intelligence strength
        intelligence_magnitude = pd.Series(0.0, index=data.index)
        for universe in universes:
            intelligence_magnitude += universe ** 2
        intelligence_magnitude = np.sqrt(intelligence_magnitude / len(universes))
        
        # 3. Universal Pattern Recognition
        # Patterns consistent across universes
        pattern_agreement = pd.Series(0.0, index=data.index)
        for universe in universes:
            pattern_agreement += (np.sign(universe) == np.sign(core_intelligence)).astype(float)
        pattern_agreement = pattern_agreement / len(universes)
        
        # Pattern strength
        pattern_strength = abs(core_intelligence) * pattern_agreement
        
        # 4. Omniversal Synthesis
        omniversal_score = (
            0.40 * core_intelligence +
            0.30 * intelligence_magnitude +
            0.30 * pattern_strength
        )
        
        # 5. Intelligence Quality
        intelligence_consistency = 1 / (1 + core_intelligence.rolling(intelligence_period).std())
        universe_coherence = pattern_agreement
        
        intelligence_quality = (intelligence_consistency + universe_coherence) / 2
        
        result = pd.DataFrame(index=data.index)
        result['omniversal_score'] = omniversal_score
        result['core_intelligence'] = core_intelligence
        result['intelligence_magnitude'] = intelligence_magnitude
        result['pattern_agreement'] = pattern_agreement
        result['intelligence_quality'] = intelligence_quality
        result['universe_trend'] = universe_trend
        result['universe_momentum'] = universe_momentum
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['omniversal_score'] > 0.6) &
            (indicator['intelligence_quality'] > 0.7) &
            (indicator['pattern_agreement'] > 0.7)
        )
        
        tp_pips = params.get('tp_pips', 250)
        sl_pips = params.get('sl_pips', 100)
        pip_value = 0.0001
        
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
        
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        signal_strength = indicator['omniversal_score'].clip(-1, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on intelligence loss"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['omniversal_score'] > 0.6) &
            (indicator['intelligence_quality'] > 0.7) &
            (indicator['pattern_agreement'] > 0.7)
        )
        
        exits = (
            (indicator['omniversal_score'] < 0) |
            (indicator['intelligence_quality'] < 0.3)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['omniversal_score'] < 0)] = 'intelligence_reversal'
        exit_reason[exits & (indicator['intelligence_quality'] < 0.3)] = 'quality_collapse'
        
        signal_strength = indicator['omniversal_score'].clip(-1, 1)
        
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
        features['omniversal_score'] = indicator['omniversal_score']
        features['core_intelligence'] = indicator['core_intelligence']
        features['intelligence_magnitude'] = indicator['intelligence_magnitude']
        features['pattern_agreement'] = indicator['pattern_agreement']
        features['intelligence_quality'] = indicator['intelligence_quality']
        features['universe_trend'] = indicator['universe_trend']
        features['universe_momentum'] = indicator['universe_momentum']
        features['intelligence_momentum'] = indicator['omniversal_score'].diff(5)
        features['quality_trend'] = indicator['intelligence_quality'].rolling(10).mean()
        features['agreement_stability'] = indicator['pattern_agreement'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'omniversal_period': [89, 100, 125, 144, 200],
            'intelligence_period': [55, 75, 89, 100, 125],
            'core_period': [34, 40, 55, 75, 100],
            'tp_pips': [150, 200, 250, 300, 400],
            'sl_pips': [60, 75, 100, 125, 150]
        }
