"""415 - Inventory Risk Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_InventoryRisk:
    """Inventory Risk - Market maker inventory risk"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "InventoryRisk", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Simulate inventory accumulation
        # Buy = +inventory, Sell = -inventory
        
        trade_direction = np.sign(data['close'] - data['open'])
        trade_size = data['volume']
        
        # Inventory change
        inventory_change = trade_direction * trade_size
        
        # Cumulative inventory
        cumulative_inventory = inventory_change.rolling(period).sum()
        
        # Inventory risk = inventory * volatility
        volatility = data['close'].pct_change().rolling(period).std()
        inventory_risk = abs(cumulative_inventory) * volatility
        
        # Normalize
        inventory_risk_normalized = inventory_risk / (inventory_risk.rolling(50).max() + 1e-10)
        
        # Inventory imbalance
        total_volume = trade_size.rolling(period).sum()
        inventory_imbalance = cumulative_inventory / (total_volume + 1e-10)
        
        # Risk score
        risk_score = inventory_risk_normalized
        
        # Safety score (low risk)
        safety = 1 - risk_score
        
        # Smooth
        safety_smooth = safety.rolling(5).mean()
        
        return pd.DataFrame({
            'inventory_change': inventory_change,
            'cumulative_inventory': cumulative_inventory,
            'inventory_risk': inventory_risk,
            'inventory_risk_normalized': inventory_risk_normalized,
            'inventory_imbalance': inventory_imbalance,
            'risk_score': risk_score,
            'safety': safety,
            'safety_smooth': safety_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low inventory risk
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
        
        # Exit: Risky
        exits = result['safety'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_inventory_risk', index=data.index),
            'signal_strength': result['safety_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['inventory_change'] = result['inventory_change']
        features['inventory_cumulative'] = result['cumulative_inventory']
        features['inventory_risk'] = result['inventory_risk']
        features['inventory_risk_normalized'] = result['inventory_risk_normalized']
        features['inventory_imbalance'] = result['inventory_imbalance']
        features['inventory_risk_score'] = result['risk_score']
        features['inventory_safety'] = result['safety']
        features['inventory_safety_smooth'] = result['safety_smooth']
        features['inventory_low_risk'] = (result['safety'] > 0.6).astype(int)
        
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

