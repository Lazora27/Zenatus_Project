"""429 - Urgency Cost"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_UrgencyCost:
    """Urgency Cost - Cost of fast execution"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "UrgencyCost", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Urgency measured by volume spike
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_spike = volume / (avg_volume + 1e-10)
        
        # Price impact during urgency
        price_change = abs(data['close'] - data['open'])
        
        # Urgency cost = price_impact * volume_spike
        urgency_cost = price_change * volume_spike
        
        # Relative urgency cost
        relative_urgency = urgency_cost / data['close']
        
        # Average urgency cost
        avg_urgency = relative_urgency.rolling(period).mean()
        
        # Urgency volatility
        urgency_volatility = relative_urgency.rolling(period).std()
        
        # High urgency periods
        urgency_threshold = volume_spike.rolling(50).quantile(0.8)
        high_urgency = (volume_spike > urgency_threshold).astype(int)
        
        # Efficiency (low urgency cost)
        efficiency = 1 / (avg_urgency + 1e-10)
        efficiency_normalized = efficiency / efficiency.rolling(50).max()
        
        # Smooth
        efficiency_smooth = efficiency_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'volume_spike': volume_spike,
            'price_change': price_change,
            'urgency_cost': urgency_cost,
            'relative_urgency': relative_urgency,
            'avg_urgency': avg_urgency,
            'urgency_volatility': urgency_volatility,
            'high_urgency': high_urgency,
            'efficiency': efficiency_normalized,
            'efficiency_smooth': efficiency_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low urgency cost
        entries = result['efficiency_smooth'] > 0.6
        
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
            'signal_strength': result['efficiency_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Efficient
        entries = result['efficiency'] > 0.6
        
        # Exit: High urgency
        exits = result['high_urgency'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_urgency', index=data.index),
            'signal_strength': result['efficiency_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['urgency_volume_spike'] = result['volume_spike']
        features['urgency_price_change'] = result['price_change']
        features['urgency_cost'] = result['urgency_cost']
        features['urgency_relative'] = result['relative_urgency']
        features['urgency_avg'] = result['avg_urgency']
        features['urgency_volatility'] = result['urgency_volatility']
        features['urgency_high'] = result['high_urgency']
        features['urgency_efficiency'] = result['efficiency']
        features['urgency_efficiency_smooth'] = result['efficiency_smooth']
        features['urgency_low_cost'] = (result['efficiency'] > 0.6).astype(int)
        
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

