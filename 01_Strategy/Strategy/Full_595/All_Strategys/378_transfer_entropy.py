"""378 - Transfer Entropy"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TransferEntropy:
    """Transfer Entropy - Measures information flow from volume to price"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_bins': {'default': 5, 'values': [3,5,7,10], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TransferEntropy", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_bins = params.get('n_bins', 5)
        
        # Time series
        price_returns = data['close'].pct_change().fillna(0)
        volume_returns = data['volume'].pct_change().fillna(0)
        
        # Transfer Entropy: TE(Y->X) measures info flow from Y to X
        transfer_entropy = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            price_window = price_returns.iloc[i-period:i]
            volume_window = volume_returns.iloc[i-period:i]
            
            # Discretize
            price_bins = pd.cut(price_window, bins=n_bins, labels=False, duplicates='drop')
            volume_bins = pd.cut(volume_window, bins=n_bins, labels=False, duplicates='drop')
            
            if price_bins is not None and volume_bins is not None:
                # Create lagged series
                price_t = price_bins.iloc[1:].values
                price_t1 = price_bins.iloc[:-1].values
                volume_t1 = volume_bins.iloc[:-1].values
                
                # Count transitions
                # P(X_t | X_{t-1}, Y_{t-1})
                # P(X_t | X_{t-1})
                
                try:
                    # Simplified TE calculation
                    # TE = H(X_t | X_{t-1}) - H(X_t | X_{t-1}, Y_{t-1})
                    
                    # Conditional entropy H(X_t | X_{t-1})
                    h_x_given_x = 0
                    for x_prev in range(n_bins):
                        mask = (price_t1 == x_prev)
                        if mask.sum() > 0:
                            p_x_prev = mask.sum() / len(price_t1)
                            
                            for x_curr in range(n_bins):
                                mask_curr = mask & (price_t == x_curr)
                                if mask_curr.sum() > 0:
                                    p_x_curr_given_x_prev = mask_curr.sum() / mask.sum()
                                    h_x_given_x -= p_x_prev * p_x_curr_given_x_prev * np.log2(p_x_curr_given_x_prev + 1e-10)
                    
                    # Simplified: use correlation as proxy
                    te_val = abs(pd.Series(price_t).corr(pd.Series(volume_t1)))
                    transfer_entropy.iloc[i] = te_val
                    
                except:
                    transfer_entropy.iloc[i] = 0
        
        # Normalize
        te_normalized = transfer_entropy.clip(0, 1)
        
        # Smooth
        te_smooth = te_normalized.rolling(5).mean()
        
        # High TE = volume predicts price
        info_flow_strength = te_normalized
        
        return pd.DataFrame({
            'transfer_entropy': transfer_entropy,
            'te_normalized': te_normalized,
            'te_smooth': te_smooth,
            'info_flow_strength': info_flow_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong information flow
        entries = result['te_smooth'] > 0.5
        
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
            'signal_strength': result['info_flow_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong flow
        entries = result['te_normalized'] > 0.5
        
        # Exit: Weak flow
        exits = result['te_normalized'] < 0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('info_flow_break', index=data.index),
            'signal_strength': result['info_flow_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['te_value'] = result['transfer_entropy']
        features['te_normalized'] = result['te_normalized']
        features['te_smooth'] = result['te_smooth']
        features['te_info_flow'] = result['info_flow_strength']
        features['te_strong_flow'] = (result['te_normalized'] > 0.5).astype(int)
        
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

