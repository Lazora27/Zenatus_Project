"""328 - Multi-Model Fusion"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MultiModelFusion:
    """Multi-Model Fusion - Fuses predictions from multiple model types"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MultiModelFusion", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Model 1: Linear regression
        x = np.arange(period)
        linear_pred = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            y = data['close'].iloc[i-period:i].values
            if len(y) == period:
                slope = np.polyfit(x, y, 1)[0]
                linear_pred.iloc[i] = slope
        
        linear_signal = (linear_pred > 0).astype(float)
        
        # Model 2: Exponential smoothing
        exp_smooth = data['close'].ewm(span=period).mean()
        exp_signal = (data['close'] > exp_smooth).astype(float)
        
        # Model 3: ARIMA-like (autoregressive)
        ar_pred = pd.Series(0.0, index=data.index)
        for i in range(period, len(data)):
            # Simple AR(1)
            returns = data['close'].pct_change().iloc[i-period:i]
            if len(returns) > 0:
                ar_coef = returns.autocorr(lag=1)
                if not np.isnan(ar_coef):
                    ar_pred.iloc[i] = ar_coef * returns.iloc[-1]
        
        ar_signal = (ar_pred > 0).astype(float)
        
        # Model 4: Volatility-based
        returns = data['close'].pct_change()
        volatility = returns.rolling(period).std()
        vol_signal = (volatility < volatility.rolling(50).median()).astype(float)
        
        # Fusion: weighted average
        fusion_score = (
            0.3 * linear_signal +
            0.3 * exp_signal +
            0.2 * ar_signal +
            0.2 * vol_signal
        )
        
        # Smooth
        fusion_smooth = fusion_score.rolling(5).mean()
        
        # Model agreement
        models = pd.DataFrame({
            'linear': linear_signal,
            'exp': exp_signal,
            'ar': ar_signal,
            'vol': vol_signal
        })
        
        agreement = models.std(axis=1)
        confidence = 1 - agreement
        
        return pd.DataFrame({
            'fusion_score': fusion_score,
            'fusion_smooth': fusion_smooth,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High fusion score
        entries = result['fusion_smooth'] > 0.6
        
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
            'signal_strength': result['confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['fusion_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['fusion_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('fusion_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['fusion_score'] = result['fusion_score']
        features['fusion_smooth'] = result['fusion_smooth']
        features['fusion_confidence'] = result['confidence']
        features['fusion_high_score'] = (result['fusion_smooth'] > 0.6).astype(int)
        features['fusion_low_score'] = (result['fusion_smooth'] < 0.4).astype(int)
        features['fusion_high_confidence'] = (result['confidence'] > 0.7).astype(int)
        
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

