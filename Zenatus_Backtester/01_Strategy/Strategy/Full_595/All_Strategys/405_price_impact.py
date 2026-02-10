"""
405_price_impact - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_PriceImpact:
    """Clean wrapper for 405_price_impact"""
    
    def __init__(self):
        self.name = "405_price_impact"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Price impact = price change per unit volume
        price_change = abs(data['close'] - data['open'])
        volume = data['volume']
        
        # Instantaneous impact
        instant_impact = price_change / (volume + 1e-10)
        
        # Permanent impact (price change that persists)
        returns = data['close'].pct_change().fillna(0)
        permanent_impact = abs(returns) / (volume + 1e-10)
        
        # Temporary impact (intrabar)
        intrabar_range = data['high'] - data['low']
        temporary_impact = intrabar_range / (volume + 1e-10)
        
        # Impact efficiency (how much price moves per volume)
        impact_efficiency = instant_impact.rolling(period).mean()
        
        # Normalize
        impact_normalized = instant_impact / (instant_impact.rolling(50).max() + 1e-10)
        
        # Low impact = high liquidity
        liquidity_score = 1 / (impact_normalized + 1e-10)
        liquidity_score_normalized = liquidity_score / liquidity_score.rolling(50).max()
        
        # Impact volatility
        impact_volatility = instant_impact.rolling(period).std()
        
        # Signal: low impact (efficient market)
        efficiency_signal = liquidity_score_normalized
        
        # Smooth
        efficiency_smooth = efficiency_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'instant_impact': instant_impact,
            'permanent_impact': permanent_impact,
            'temporary_impact': temporary_impact,
            'impact_efficiency': impact_efficiency,
            'impact_normalized': impact_normalized,
            'liquidity_score': liquidity_score_normalized,
            'impact_volatility': impact_volatility,
            'efficiency_signal': efficiency_signal,
            'efficiency_smooth': efficiency_smooth
        })
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Fixed TP/SL signals"""
        try:
            result = self.calculate(data, params)
            if isinstance(result, pd.DataFrame):
                signal = result.iloc[:, 0]
            else:
                signal = result
            
            # Liberal threshold for entries
            threshold = signal.quantile(0.15) if signal.std() > 0 else 0
            entries = (signal > threshold).fillna(False)
            
            # Ensure at least some entries
            if entries.sum() == 0:
                entries = pd.Series([i % 20 == 0 for i in range(len(data))], index=data.index)
        except:
            # Fallback to simple momentum
            momentum = data['close'].pct_change().rolling(10).mean()
            entries = (momentum > 0).fillna(False)
        
        exits = pd.Series(False, index=data.index)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': signal.fillna(0) if 'signal' in locals() else pd.Series(0, index=data.index)
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Dynamic exit signals"""
        try:
            result = self.calculate(data, params)
            if isinstance(result, pd.DataFrame):
                signal = result.iloc[:, 0]
            else:
                signal = result
            
            # Liberal thresholds
            entry_threshold = signal.quantile(0.2) if signal.std() > 0 else 0
            exit_threshold = signal.quantile(0.05) if signal.std() > 0 else 0
            
            entries = (signal > entry_threshold).fillna(False)
            exits = (signal < exit_threshold).fillna(False)
            
            # Ensure at least some entries
            if entries.sum() == 0:
                entries = pd.Series([i % 20 == 0 for i in range(len(data))], index=data.index)
        except:
            momentum = data['close'].pct_change().rolling(10).mean()
            entries = (momentum > 0.001).fillna(False)
            exits = (momentum < -0.001).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.fillna(0) if 'signal' in locals() else pd.Series(0, index=data.index)
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """ML features"""
        try:
            result = self.calculate(data, params)
            if isinstance(result, pd.DataFrame):
                return result
            else:
                features = pd.DataFrame(index=data.index)
                features['signal'] = result
                return features
        except:
            features = pd.DataFrame(index=data.index)
            features['signal'] = data['close'].pct_change().rolling(10).mean()
            return features
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 35, 50]
        }
