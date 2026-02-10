"""414 - Adverse Selection Cost"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AdverseSelection:
    """Adverse Selection - Cost of trading against informed traders"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AdverseSelection", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Adverse selection = post-trade price movement
        # If price continues in trade direction = adverse selection
        
        # Trade direction (buy/sell)
        trade_direction = np.sign(data['close'] - data['open'])
        
        # Post-trade price movement
        future_return = data['close'].pct_change().shift(-1).fillna(0)
        
        # Adverse selection cost
        # If bought and price goes up = adverse (paid too much)
        adverse_cost = trade_direction * future_return
        
        # Average adverse selection
        avg_adverse = adverse_cost.rolling(period).mean()
        
        # Adverse selection volatility
        adverse_volatility = adverse_cost.rolling(period).std()
        
        # Cumulative adverse selection
        cumulative_adverse = adverse_cost.rolling(period).sum()
        
        # Safety score (low adverse selection)
        safety = 1 / (abs(avg_adverse) + 1e-10)
        safety_normalized = safety / safety.rolling(50).max()
        
        # Smooth
        safety_smooth = safety_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'trade_direction': trade_direction,
            'adverse_cost': adverse_cost,
            'avg_adverse': avg_adverse,
            'adverse_volatility': adverse_volatility,
            'cumulative_adverse': cumulative_adverse,
            'safety': safety_normalized,
            'safety_smooth': safety_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low adverse selection
        entries = result['safety_smooth'] > 0.7
        
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
        entries = result['safety'] > 0.7
        
        # Exit: High adverse selection
        exits = result['safety'] < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('adverse_selection', index=data.index),
            'signal_strength': result['safety_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['adverse_direction'] = result['trade_direction']
        features['adverse_cost'] = result['adverse_cost']
        features['adverse_avg'] = result['avg_adverse']
        features['adverse_volatility'] = result['adverse_volatility']
        features['adverse_cumulative'] = result['cumulative_adverse']
        features['adverse_safety'] = result['safety']
        features['adverse_safety_smooth'] = result['safety_smooth']
        features['adverse_safe'] = (result['safety'] > 0.7).astype(int)
        
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

