"""202 - Volume at Price"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeAtPrice:
    """Volume at Price - Current Price Level Volume"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [20,30,50,75,100], 'optimize': True},
        'price_tolerance': {'default': 0.001, 'values': [0.0005,0.001,0.002,0.005], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeAtPrice", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        tolerance = params.get('price_tolerance', 0.001)
        
        close, volume = data['close'], data['volume']
        
        # Volume at current price level
        vap = pd.Series(0.0, index=data.index)
        vap_percentile = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            current_price = close.iloc[i]
            window_prices = close.iloc[i-period:i]
            window_volumes = volume.iloc[i-period:i]
            
            # Volume bei ähnlichen Preisen
            price_mask = abs(window_prices - current_price) / current_price < tolerance
            vap.iloc[i] = window_volumes[price_mask].sum()
            
            # Percentile ranking
            all_vaps = []
            for j in range(len(window_prices)):
                price_j = window_prices.iloc[j]
                mask_j = abs(window_prices - price_j) / price_j < tolerance
                all_vaps.append(window_volumes[mask_j].sum())
            
            if all_vaps:
                vap_percentile.iloc[i] = (np.array(all_vaps) < vap.iloc[i]).sum() / len(all_vaps)
        
        # Relative VAP
        avg_volume = volume.rolling(period).mean()
        vap_ratio = vap / (avg_volume + 1e-10)
        
        # High/Low Volume Nodes
        high_volume_node = (vap_percentile > 0.8).astype(int)
        low_volume_node = (vap_percentile < 0.2).astype(int)
        
        return pd.DataFrame({
            'vap': vap,
            'vap_percentile': vap_percentile,
            'vap_ratio': vap_ratio,
            'high_volume_node': high_volume_node,
            'low_volume_node': low_volume_node
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vap_data = self.calculate(data, params)
        # Entry bei High Volume Node (Support/Resistance)
        entries = (vap_data['high_volume_node'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vap_data['vap_percentile']}
    
    def generate_signals_dynamic(self, data, params):
        vap_data = self.calculate(data, params)
        entries = (vap_data['high_volume_node'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (vap_data['low_volume_node'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('low_volume_node', index=data.index),
                'signal_strength': vap_data['vap_percentile']}
    
    def get_ml_features(self, data, params):
        vap_data = self.calculate(data, params)
        return pd.DataFrame({
            'vap': vap_data['vap'],
            'vap_percentile': vap_data['vap_percentile'],
            'vap_ratio': vap_data['vap_ratio'],
            'high_volume_node': vap_data['high_volume_node'],
            'low_volume_node': vap_data['low_volume_node'],
            'vap_change': vap_data['vap'].pct_change()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
