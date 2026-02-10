"""204 - Value Area High (VAH)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ValueAreaHigh:
    """Value Area High - Upper Boundary of 70% Volume"""
    PARAMETERS = {
        'period': {'default': 100, 'values': [50,75,100,150,200], 'optimize': True},
        'bins': {'default': 20, 'values': [10,15,20,25,30], 'optimize': True},
        'value_area_pct': {'default': 0.7, 'values': [0.6,0.65,0.7,0.75,0.8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ValueAreaHigh", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 100)
        bins = params.get('bins', 20)
        va_pct = params.get('value_area_pct', 0.7)
        
        close, volume = data['close'], data['volume']
        
        vah = pd.Series(0.0, index=data.index)
        val = pd.Series(0.0, index=data.index)
        va_width = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window_prices = close.iloc[i-period:i]
            window_volumes = volume.iloc[i-period:i]
            
            price_min, price_max = window_prices.min(), window_prices.max()
            if price_max > price_min:
                price_bins = np.linspace(price_min, price_max, bins)
                bin_volumes = np.zeros(bins-1)
                
                for j, price in enumerate(window_prices):
                    bin_idx = np.searchsorted(price_bins, price) - 1
                    if 0 <= bin_idx < len(bin_volumes):
                        bin_volumes[bin_idx] += window_volumes.iloc[j]
                
                # Value Area berechnen
                total_vol = bin_volumes.sum()
                target_vol = total_vol * va_pct
                sorted_bins = np.argsort(bin_volumes)[::-1]
                
                cumsum = 0
                value_area_bins = []
                for idx in sorted_bins:
                    cumsum += bin_volumes[idx]
                    value_area_bins.append(idx)
                    if cumsum >= target_vol:
                        break
                
                if value_area_bins:
                    vah.iloc[i] = price_bins[max(value_area_bins)+1]
                    val.iloc[i] = price_bins[min(value_area_bins)]
                    va_width.iloc[i] = vah.iloc[i] - val.iloc[i]
        
        # Distance from VAH
        distance_vah = (close - vah) / close
        
        # Above/Below VAH
        above_vah = (close > vah).astype(int)
        below_vah = (close < vah).astype(int)
        
        # VAH as Resistance
        near_vah = (abs(close - vah) / close < 0.01).astype(int)
        
        return pd.DataFrame({
            'vah': vah,
            'val': val,
            'va_width': va_width,
            'distance_vah': distance_vah,
            'above_vah': above_vah,
            'below_vah': below_vah,
            'near_vah': near_vah
        }, index=data.index).fillna(method='ffill').fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vah_data = self.calculate(data, params)
        # Entry wenn Preis VAH durchbricht (Breakout)
        entries = (data['close'] > vah_data['vah']) & (data['close'].shift(1) <= vah_data['vah'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(vah_data['distance_vah'])}
    
    def generate_signals_dynamic(self, data, params):
        vah_data = self.calculate(data, params)
        entries = (data['close'] > vah_data['vah']) & (data['close'].shift(1) <= vah_data['vah'].shift(1))
        exits = (data['close'] < vah_data['val']) & (data['close'].shift(1) >= vah_data['val'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_val', index=data.index),
                'signal_strength': abs(vah_data['distance_vah'])}
    
    def get_ml_features(self, data, params):
        vah_data = self.calculate(data, params)
        return pd.DataFrame({
            'vah': vah_data['vah'],
            'val': vah_data['val'],
            'va_width': vah_data['va_width'],
            'distance_vah': vah_data['distance_vah'],
            'above_vah': vah_data['above_vah'],
            'near_vah': vah_data['near_vah']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
