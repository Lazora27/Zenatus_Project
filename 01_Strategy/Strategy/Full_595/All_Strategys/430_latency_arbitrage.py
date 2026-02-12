"""430 - Latency Arbitrage Detector"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_LatencyArbitrage:
    """Latency Arbitrage - Detects fast price movements (HFT activity)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "LatencyArbitrage", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Fast price movements (within bar)
        intrabar_range = data['high'] - data['low']
        
        # Price velocity (range per unit time)
        price_velocity = intrabar_range
        
        # Average velocity
        avg_velocity = price_velocity.rolling(period).mean()
        
        # Velocity spike (HFT activity)
        velocity_spike = price_velocity / (avg_velocity + 1e-10)
        
        # Price reversal (fast move then reversal = latency arb)
        price_change = data['close'] - data['open']
        reversal = abs(price_change) < (intrabar_range * 0.3)
        
        # Latency arbitrage score
        latency_score = velocity_spike * reversal.astype(int)
        
        # Average latency activity
        avg_latency = latency_score.rolling(period).mean()
        
        # High latency periods
        latency_threshold = latency_score.rolling(50).quantile(0.8)
        high_latency = (latency_score > latency_threshold).astype(int)
        
        # Safety score (low latency activity = safe)
        safety = 1 / (avg_latency + 1e-10)
        safety_normalized = safety / safety.rolling(50).max()
        
        # Smooth
        safety_smooth = safety_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'intrabar_range': intrabar_range,
            'price_velocity': price_velocity,
            'avg_velocity': avg_velocity,
            'velocity_spike': velocity_spike,
            'reversal': reversal.astype(int),
            'latency_score': latency_score,
            'avg_latency': avg_latency,
            'high_latency': high_latency,
            'safety': safety_normalized,
            'safety_smooth': safety_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low latency activity (safe)
        entries = result['safety_smooth'] > 0.6
        
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
            'signal_strength': result['safety_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe
        entries = result['safety'] > 0.6
        
        # Exit: High latency activity
        exits = result['high_latency'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('latency_arbitrage', index=data.index),
            'signal_strength': result['safety_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['latency_intrabar_range'] = result['intrabar_range']
        features['latency_price_velocity'] = result['price_velocity']
        features['latency_avg_velocity'] = result['avg_velocity']
        features['latency_velocity_spike'] = result['velocity_spike']
        features['latency_reversal'] = result['reversal']
        features['latency_score'] = result['latency_score']
        features['latency_avg'] = result['avg_latency']
        features['latency_high'] = result['high_latency']
        features['latency_safety'] = result['safety']
        features['latency_safety_smooth'] = result['safety_smooth']
        features['latency_safe'] = (result['safety'] > 0.6).astype(int)
        
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

