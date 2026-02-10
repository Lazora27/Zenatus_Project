"""423 - Quote Rule Classification"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_QuoteRule:
    """Quote Rule - Classifies trades relative to mid-quote"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "QuoteRule", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Mid-quote (bid + ask) / 2
        mid_quote = (data['high'] + data['low']) / 2
        
        # Trade price
        trade_price = data['close']
        
        # Quote rule classification
        # Above mid = buyer-initiated, Below mid = seller-initiated
        buyer_initiated = (trade_price > mid_quote).astype(int)
        seller_initiated = (trade_price < mid_quote).astype(int)
        at_mid = (trade_price == mid_quote).astype(int)
        
        # Classification signal
        classification = pd.Series(0, index=data.index)
        classification[buyer_initiated == 1] = 1
        classification[seller_initiated == 1] = -1
        
        # Volume-weighted classification
        buyer_volume = data['volume'] * buyer_initiated
        seller_volume = data['volume'] * seller_initiated
        
        # Volume imbalance
        volume_imbalance = buyer_volume - seller_volume
        
        # Cumulative imbalance
        cumulative_imbalance = volume_imbalance.rolling(period).sum()
        
        # Buyer ratio
        total_volume = data['volume'].rolling(period).sum()
        buyer_ratio = buyer_volume.rolling(period).sum() / (total_volume + 1e-10)
        
        # Distance from mid
        distance_from_mid = (trade_price - mid_quote) / mid_quote
        
        # Signal
        signal = buyer_ratio
        
        # Smooth
        signal_smooth = signal.rolling(5).mean()
        
        return pd.DataFrame({
            'mid_quote': mid_quote,
            'classification': classification,
            'buyer_initiated': buyer_initiated,
            'seller_initiated': seller_initiated,
            'buyer_volume': buyer_volume,
            'seller_volume': seller_volume,
            'volume_imbalance': volume_imbalance,
            'cumulative_imbalance': cumulative_imbalance,
            'buyer_ratio': buyer_ratio,
            'distance_from_mid': distance_from_mid,
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
        
        features['quote_rule_mid'] = result['mid_quote']
        features['quote_rule_classification'] = result['classification']
        features['quote_rule_buyer_initiated'] = result['buyer_initiated']
        features['quote_rule_seller_initiated'] = result['seller_initiated']
        features['quote_rule_buyer_volume'] = result['buyer_volume']
        features['quote_rule_seller_volume'] = result['seller_volume']
        features['quote_rule_volume_imbalance'] = result['volume_imbalance']
        features['quote_rule_cumulative_imbalance'] = result['cumulative_imbalance']
        features['quote_rule_buyer_ratio'] = result['buyer_ratio']
        features['quote_rule_distance_from_mid'] = result['distance_from_mid']
        features['quote_rule_signal'] = result['signal']
        features['quote_rule_signal_smooth'] = result['signal_smooth']
        features['quote_rule_buyer_pressure'] = (result['buyer_ratio'] > 0.6).astype(int)
        
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

