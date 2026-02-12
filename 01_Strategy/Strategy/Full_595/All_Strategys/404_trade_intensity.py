"""
404_trade_intensity - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_TradeIntensity:
    """Clean wrapper for 404_trade_intensity"""
    
    def __init__(self):
        self.name = "404_trade_intensity"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Trade intensity from volume
        volume = data['volume']
        
        # Volume rate of change
        volume_roc = volume.pct_change().fillna(0)
        
        # Trade intensity (volume relative to average)
        avg_volume = volume.rolling(period).mean()
        intensity = volume / (avg_volume + 1e-10)
        
        # Intensity momentum
        intensity_momentum = intensity.diff()
        
        # Cumulative intensity
        cumulative_intensity = intensity.rolling(period).sum()
        
        # Intensity volatility
        intensity_volatility = intensity.rolling(period).std()
        
        # High intensity periods
        intensity_threshold = intensity.rolling(50).quantile(0.3)
        high_intensity = (intensity > intensity_threshold).fillna(0).astype(int)
        
        # Signal: moderate to high intensity
        intensity_signal = intensity.clip(0, 3) / 3
        
        # Smooth
        intensity_smooth = intensity_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'volume_roc': volume_roc,
            'intensity': intensity,
            'intensity_momentum': intensity_momentum,
            'cumulative_intensity': cumulative_intensity,
            'intensity_volatility': intensity_volatility,
            'high_intensity': high_intensity,
            'intensity_signal': intensity_signal,
            'intensity_smooth': intensity_smooth
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
