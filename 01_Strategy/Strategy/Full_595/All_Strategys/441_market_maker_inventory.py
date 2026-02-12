"""441 - Market Maker Inventory Risk"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MarketMakerInventory:
    """Market Maker Inventory - Tracks market maker inventory risk"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MarketMakerInventory", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Inventory accumulation (buy/sell imbalance)
        price_change = data['close'].diff()
        volume = data['volume']
        
        # Signed volume (buy=positive, sell=negative)
        signed_volume = volume * np.sign(price_change)
        
        # Cumulative inventory
        inventory = signed_volume.rolling(period).sum()
        
        # Inventory risk (normalized)
        inventory_std = inventory.rolling(period).std()
        inventory_risk = abs(inventory) / (inventory_std + 1e-10)
        inventory_risk_normalized = inventory_risk / inventory_risk.rolling(50).max()
        
        # Inventory pressure (directional)
        inventory_pressure = inventory / (volume.rolling(period).sum() + 1e-10)
        
        # Mean reversion tendency (high inventory = reversion pressure)
        reversion_pressure = abs(inventory_pressure)
        reversion_signal = -np.sign(inventory_pressure)  # Opposite direction
        
        # Inventory turnover (how fast inventory clears)
        inventory_change = abs(inventory.diff())
        turnover = inventory_change / (abs(inventory) + 1e-10)
        turnover_smooth = turnover.rolling(5).mean()
        
        # Market maker stress (high inventory + low turnover)
        mm_stress = inventory_risk_normalized * (1 - turnover_smooth)
        mm_stress_smooth = mm_stress.rolling(5).mean()
        
        # Optimal trading conditions (low stress)
        optimal_conditions = mm_stress_smooth < 0.4
        
        # Inventory imbalance score
        imbalance_score = abs(inventory_pressure)
        imbalance_score_smooth = imbalance_score.rolling(5).mean()
        
        # Risk-adjusted opportunity
        opportunity = reversion_pressure * (1 - mm_stress_smooth)
        opportunity_smooth = opportunity.rolling(5).mean()
        
        return pd.DataFrame({
            'signed_volume': signed_volume,
            'inventory': inventory,
            'inventory_std': inventory_std,
            'inventory_risk': inventory_risk_normalized,
            'inventory_pressure': inventory_pressure,
            'reversion_pressure': reversion_pressure,
            'reversion_signal': reversion_signal,
            'turnover': turnover,
            'turnover_smooth': turnover_smooth,
            'mm_stress': mm_stress,
            'mm_stress_smooth': mm_stress_smooth,
            'optimal_conditions': optimal_conditions.astype(int),
            'imbalance_score': imbalance_score,
            'imbalance_score_smooth': imbalance_score_smooth,
            'opportunity': opportunity,
            'opportunity_smooth': opportunity_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High reversion opportunity, low stress
        entries = (result['opportunity_smooth'] > 0.5) & (result['optimal_conditions'] == 1)
        
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
            'signal_strength': result['opportunity_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions
        entries = result['optimal_conditions'] == 1
        
        # Exit: High stress
        exits = result['mm_stress_smooth'] > 0.6
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_mm_stress', index=data.index),
            'signal_strength': result['opportunity_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['mm_signed_volume'] = result['signed_volume']
        features['mm_inventory'] = result['inventory']
        features['mm_inventory_std'] = result['inventory_std']
        features['mm_inventory_risk'] = result['inventory_risk']
        features['mm_inventory_pressure'] = result['inventory_pressure']
        features['mm_reversion_pressure'] = result['reversion_pressure']
        features['mm_reversion_signal'] = result['reversion_signal']
        features['mm_turnover'] = result['turnover']
        features['mm_turnover_smooth'] = result['turnover_smooth']
        features['mm_stress'] = result['mm_stress']
        features['mm_stress_smooth'] = result['mm_stress_smooth']
        features['mm_optimal_conditions'] = result['optimal_conditions']
        features['mm_imbalance_score'] = result['imbalance_score']
        features['mm_imbalance_score_smooth'] = result['imbalance_score_smooth']
        features['mm_opportunity'] = result['opportunity']
        features['mm_opportunity_smooth'] = result['opportunity_smooth']
        
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

