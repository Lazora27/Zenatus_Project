"""422 - Tick Rule Classification"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TickRule:
    """Tick Rule - Classifies trades as buyer/seller initiated"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TickRule", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Tick rule: compare to previous price
        price_change = data['close'].diff()
        
        # Buyer-initiated (uptick)
        buyer_initiated = (price_change > 0).astype(int)
        
        # Seller-initiated (downtick)
        seller_initiated = (price_change < 0).astype(int)
        
        # Zero-tick (use previous classification)
        zero_tick = (price_change == 0).astype(int)
        
        # Forward-fill for zero ticks
        classification = pd.Series(0, index=data.index)
        classification[buyer_initiated == 1] = 1
        classification[seller_initiated == 1] = -1
        classification = classification.replace(0, np.nan).fillna(method='ffill').fillna(0)
        
        # Buyer/seller volume
        buyer_volume = data['volume'] * (classification == 1).astype(int)
        seller_volume = data['volume'] * (classification == -1).astype(int)
        
        # Volume imbalance
        volume_imbalance = buyer_volume - seller_volume
        
        # Cumulative imbalance
        cumulative_imbalance = volume_imbalance.rolling(period).sum()
        
        # Buyer ratio
        total_volume = data['volume'].rolling(period).sum()
        buyer_ratio = buyer_volume.rolling(period).sum() / (total_volume + 1e-10)
        
        # Signal
        signal = buyer_ratio
        
        # Smooth
        signal_smooth = signal.rolling(5).mean()
        
        return pd.DataFrame({
            'classification': classification,
            'buyer_initiated': buyer_initiated,
            'seller_initiated': seller_initiated,
            'buyer_volume': buyer_volume,
            'seller_volume': seller_volume,
            'volume_imbalance': volume_imbalance,
            'cumulative_imbalance': cumulative_imbalance,
            'buyer_ratio': buyer_ratio,
            'signal': signal,
            'signal_smooth': signal_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong buyer pressure
        entries = result['signal_smooth'] > 0.6
        
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
            'signal_strength': result['signal_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Buyer pressure
        entries = result['buyer_ratio'] > 0.6
        
        # Exit: Seller pressure
        exits = result['buyer_ratio'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('seller_pressure', index=data.index),
            'signal_strength': result['signal_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['tick_rule_classification'] = result['classification']
        features['tick_rule_buyer_initiated'] = result['buyer_initiated']
        features['tick_rule_seller_initiated'] = result['seller_initiated']
        features['tick_rule_buyer_volume'] = result['buyer_volume']
        features['tick_rule_seller_volume'] = result['seller_volume']
        features['tick_rule_volume_imbalance'] = result['volume_imbalance']
        features['tick_rule_cumulative_imbalance'] = result['cumulative_imbalance']
        features['tick_rule_buyer_ratio'] = result['buyer_ratio']
        features['tick_rule_signal'] = result['signal']
        features['tick_rule_signal_smooth'] = result['signal_smooth']
        features['tick_rule_buyer_pressure'] = (result['buyer_ratio'] > 0.6).astype(int)
        
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

