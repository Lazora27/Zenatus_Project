"""431 - Iceberg Order Detection"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_IcebergDetection:
    """Iceberg Detection - Detects hidden large orders"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "IcebergDetection", "Execution_Algorithms", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Iceberg characteristics:
        # 1. Repeated small trades at same price
        # 2. Price doesn't move despite volume
        
        # Price stability despite volume
        price_change = abs(data['close'] - data['open'])
        volume = data['volume']
        
        # Price impact (should be low for icebergs)
        price_impact = price_change / (volume + 1e-10)
        
        # Low impact = potential iceberg
        avg_impact = price_impact.rolling(period).mean()
        
        # Volume consistency (repeated similar volumes)
        volume_std = volume.rolling(period).std()
        volume_mean = volume.rolling(period).mean()
        volume_consistency = 1 / (volume_std / (volume_mean + 1e-10) + 1e-10)
        volume_consistency_normalized = volume_consistency / volume_consistency.rolling(50).max()
        
        # Iceberg score = low impact + high volume consistency
        iceberg_score = (1 / (avg_impact + 1e-10)) * volume_consistency_normalized
        iceberg_score_normalized = iceberg_score / (iceberg_score.rolling(50).max() + 1e-10)
        
        # High iceberg score = hidden liquidity
        hidden_liquidity = iceberg_score_normalized
        
        # Smooth
        hidden_liquidity_smooth = hidden_liquidity.rolling(5).mean()
        
        return pd.DataFrame({
            'price_impact': price_impact,
            'avg_impact': avg_impact,
            'volume_consistency': volume_consistency_normalized,
            'iceberg_score': iceberg_score_normalized,
            'hidden_liquidity': hidden_liquidity,
            'hidden_liquidity_smooth': hidden_liquidity_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Hidden liquidity detected
        entries = result['hidden_liquidity_smooth'] > 0.6
        
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
            'signal_strength': result['hidden_liquidity_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Iceberg detected
        entries = result['iceberg_score'] > 0.6
        
        # Exit: Iceberg exhausted
        exits = result['iceberg_score'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('iceberg_exhausted', index=data.index),
            'signal_strength': result['hidden_liquidity_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['iceberg_price_impact'] = result['price_impact']
        features['iceberg_avg_impact'] = result['avg_impact']
        features['iceberg_volume_consistency'] = result['volume_consistency']
        features['iceberg_score'] = result['iceberg_score']
        features['iceberg_hidden_liquidity'] = result['hidden_liquidity']
        features['iceberg_hidden_liquidity_smooth'] = result['hidden_liquidity_smooth']
        features['iceberg_detected'] = (result['iceberg_score'] > 0.6).astype(int)
        
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

