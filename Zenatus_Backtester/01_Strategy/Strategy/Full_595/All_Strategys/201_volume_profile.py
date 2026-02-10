"""201 - Volume Profile"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeProfile:
    """Volume Profile - Price Level Volume Distribution"""
    PARAMETERS = {
        'period': {'default': 100, 'values': [50,75,100,150,200], 'optimize': True},
        'bins': {'default': 20, 'values': [10,15,20,25,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeProfile", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 100)
        bins = params.get('bins', 20)
        
        close, volume = data['close'], data['volume']
        
        # Volume Profile berechnen
        vp_high = pd.Series(0.0, index=data.index)
        vp_low = pd.Series(0.0, index=data.index)
        vp_poc = pd.Series(0.0, index=data.index)
        vp_vah = pd.Series(0.0, index=data.index)
        vp_val = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window_prices = close.iloc[i-period:i]
            window_volumes = volume.iloc[i-period:i]
            
            # Preis-Bins erstellen
            price_min, price_max = window_prices.min(), window_prices.max()
            price_bins = np.linspace(price_min, price_max, bins)
            
            # Volume pro Bin
            bin_volumes = np.zeros(bins-1)
            for j, price in enumerate(window_prices):
                bin_idx = np.searchsorted(price_bins, price) - 1
                if 0 <= bin_idx < len(bin_volumes):
                    bin_volumes[bin_idx] += window_volumes.iloc[j]
            
            # POC (Point of Control) - Preis mit höchstem Volume
            poc_idx = np.argmax(bin_volumes)
            vp_poc.iloc[i] = (price_bins[poc_idx] + price_bins[poc_idx+1]) / 2
            
            # Value Area (70% des Volumes)
            total_vol = bin_volumes.sum()
            target_vol = total_vol * 0.7
            sorted_bins = np.argsort(bin_volumes)[::-1]
            
            cumsum = 0
            value_area_bins = []
            for idx in sorted_bins:
                cumsum += bin_volumes[idx]
                value_area_bins.append(idx)
                if cumsum >= target_vol:
                    break
            
            if value_area_bins:
                vp_vah.iloc[i] = price_bins[max(value_area_bins)+1]
                vp_val.iloc[i] = price_bins[min(value_area_bins)]
            
            vp_high.iloc[i] = price_max
            vp_low.iloc[i] = price_min
        
        # Position im Value Area
        va_position = (close - vp_val) / (vp_vah - vp_val + 1e-10)
        
        return pd.DataFrame({
            'vp_poc': vp_poc,
            'vp_vah': vp_vah,
            'vp_val': vp_val,
            'vp_high': vp_high,
            'vp_low': vp_low,
            'va_position': va_position
        }, index=data.index).fillna(method='ffill').fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vp_data = self.calculate(data, params)
        # Entry wenn Preis über POC
        entries = (data['close'] > vp_data['vp_poc']) & (data['close'].shift(1) <= vp_data['vp_poc'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vp_data['va_position'].clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        vp_data = self.calculate(data, params)
        entries = (data['close'] > vp_data['vp_poc']) & (data['close'].shift(1) <= vp_data['vp_poc'].shift(1))
        exits = (data['close'] < vp_data['vp_val']) & (data['close'].shift(1) >= vp_data['vp_val'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_value_area', index=data.index),
                'signal_strength': vp_data['va_position'].clip(0, 1)}
    
    def get_ml_features(self, data, params):
        vp_data = self.calculate(data, params)
        return pd.DataFrame({
            'vp_poc': vp_data['vp_poc'],
            'vp_vah': vp_data['vp_vah'],
            'vp_val': vp_data['vp_val'],
            'va_position': vp_data['va_position'],
            'distance_poc': (data['close'] - vp_data['vp_poc']) / data['close'],
            'va_width': (vp_data['vp_vah'] - vp_data['vp_val']) / data['close']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
