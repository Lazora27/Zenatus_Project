"""377 - Mutual Information Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MutualInformation:
    """Mutual Information - Measures dependency between price and volume"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_bins': {'default': 10, 'values': [5,10,15], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MutualInformation", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_bins = params.get('n_bins', 10)
        
        # Variables
        price_returns = data['close'].pct_change().fillna(0)
        volume_returns = data['volume'].pct_change().fillna(0)
        
        # Mutual Information
        mi = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            price_window = price_returns.iloc[i-period:i]
            volume_window = volume_returns.iloc[i-period:i]
            
            # 2D histogram
            H, xedges, yedges = np.histogram2d(
                price_window, volume_window, bins=n_bins
            )
            
            # Joint probability
            pxy = H / H.sum()
            
            # Marginal probabilities
            px = pxy.sum(axis=1)
            py = pxy.sum(axis=0)
            
            # Mutual Information: I(X;Y) = sum(p(x,y) * log(p(x,y) / (p(x)*p(y))))
            mi_val = 0
            for x in range(n_bins):
                for y in range(n_bins):
                    if pxy[x, y] > 0 and px[x] > 0 and py[y] > 0:
                        mi_val += pxy[x, y] * np.log2(pxy[x, y] / (px[x] * py[y]))
            
            mi.iloc[i] = mi_val
        
        # Normalize
        mi_normalized = mi / (np.log2(n_bins) + 1e-10)
        mi_normalized = mi_normalized.clip(0, 1)
        
        # High MI = strong dependency = predictable
        dependency_signal = mi_normalized
        
        # Smooth
        dependency_smooth = dependency_signal.rolling(5).mean()
        
        # MI change (regime shift)
        mi_change = mi.diff().abs()
        
        return pd.DataFrame({
            'mutual_information': mi,
            'mi_normalized': mi_normalized,
            'dependency_signal': dependency_signal,
            'dependency_smooth': dependency_smooth,
            'mi_change': mi_change
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong dependency
        entries = result['dependency_smooth'] > 0.5
        
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
            'signal_strength': result['dependency_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong dependency
        entries = result['dependency_signal'] > 0.5
        
        # Exit: Weak dependency
        exits = result['dependency_signal'] < 0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('dependency_break', index=data.index),
            'signal_strength': result['dependency_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['mi_value'] = result['mutual_information']
        features['mi_normalized'] = result['mi_normalized']
        features['mi_dependency'] = result['dependency_signal']
        features['mi_dependency_smooth'] = result['dependency_smooth']
        features['mi_change'] = result['mi_change']
        features['mi_strong_dependency'] = (result['dependency_signal'] > 0.5).astype(int)
        
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

