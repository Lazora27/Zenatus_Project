"""350 - Seasonal Decomposition"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SeasonalDecomposition:
    """Seasonal Decomposition - Separates trend, seasonal, and residual components"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'seasonal_period': {'default': 24, 'values': [12,24,48], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SeasonalDecomposition", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        seasonal_period = params.get('seasonal_period', 24)
        
        # Trend component (moving average)
        trend = data['close'].rolling(period, center=True).mean()
        
        # Detrend
        detrended = data['close'] - trend
        
        # Seasonal component (average by position in cycle)
        seasonal = pd.Series(0.0, index=data.index)
        
        for i in range(seasonal_period, len(data)):
            # Position in seasonal cycle
            pos = i % seasonal_period
            
            # Average detrended value at this position
            positions = [j for j in range(pos, i, seasonal_period) if j < i]
            
            if len(positions) > 0:
                seasonal.iloc[i] = detrended.iloc[positions].mean()
        
        # Residual (noise)
        residual = detrended - seasonal
        
        # Signal components
        # Trend signal
        trend_signal = (trend > trend.shift(1)).astype(float)
        
        # Seasonal signal (positive seasonal effect)
        seasonal_signal = (seasonal > 0).astype(float)
        
        # Combined signal
        decomp_signal = (trend_signal + seasonal_signal) / 2
        
        # Smooth
        decomp_smooth = decomp_signal.rolling(5).mean()
        
        # Residual strength (low residual = good fit)
        residual_strength = 1 - abs(residual).rolling(period).mean() / data['close'].rolling(period).std()
        residual_strength = residual_strength.clip(0, 1)
        
        return pd.DataFrame({
            'trend': trend,
            'seasonal': seasonal,
            'residual': residual,
            'decomp_signal': decomp_signal,
            'decomp_smooth': decomp_smooth,
            'residual_strength': residual_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong decomposition signal
        entries = result['decomp_smooth'] > 0.6
        
        # Manual TP/SL
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': result['residual_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong signal
        entries = result['decomp_smooth'] > 0.6
        
        # Exit: Weak signal
        exits = result['decomp_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('seasonal_reversal', index=data.index),
            'signal_strength': result['residual_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['seasonal_trend'] = result['trend']
        features['seasonal_component'] = result['seasonal']
        features['seasonal_residual'] = result['residual']
        features['seasonal_signal'] = result['decomp_signal']
        features['seasonal_smooth'] = result['decomp_smooth']
        features['seasonal_strength'] = result['residual_strength']
        features['seasonal_strong'] = (result['decomp_smooth'] > 0.6).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass

    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100, 150],
            'sl_pips': [15, 25, 35, 50, 75]
        }

