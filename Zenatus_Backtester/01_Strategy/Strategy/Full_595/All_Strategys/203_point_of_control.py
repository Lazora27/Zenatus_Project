"""203 - Point of Control (POC)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PointOfControl:
    """Point of Control - Price with Highest Volume"""
    PARAMETERS = {
        'period': {'default': 100, 'values': [50,75,100,150,200], 'optimize': True},
        'bins': {'default': 20, 'values': [10,15,20,25,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PointOfControl", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 100)
        bins = params.get('bins', 20)
        
        close, volume = data['close'], data['volume']
        
        # POC berechnen
        poc = pd.Series(0.0, index=data.index)
        poc_volume = pd.Series(0.0, index=data.index)
        
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
                
                poc_idx = np.argmax(bin_volumes)
                poc.iloc[i] = (price_bins[poc_idx] + price_bins[poc_idx+1]) / 2
                poc_volume.iloc[i] = bin_volumes[poc_idx]
        
        # Distance from POC
        distance_poc = (close - poc) / close
        
        # POC als Support/Resistance
        above_poc = (close > poc).astype(int)
        below_poc = (close < poc).astype(int)
        
        # POC Movement
        poc_change = poc.diff()
        poc_trend = (poc > poc.shift(5)).astype(int)
        
        return pd.DataFrame({
            'poc': poc,
            'poc_volume': poc_volume,
            'distance_poc': distance_poc,
            'above_poc': above_poc,
            'below_poc': below_poc,
            'poc_change': poc_change,
            'poc_trend': poc_trend
        }, index=data.index).fillna(method='ffill').fillna(0)
    
    def generate_signals_fixed(self, data, params):
        poc_data = self.calculate(data, params)
        # Entry wenn Preis POC von unten kreuzt
        entries = (data['close'] > poc_data['poc']) & (data['close'].shift(1) <= poc_data['poc'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(poc_data['distance_poc'])}
    
    def generate_signals_dynamic(self, data, params):
        poc_data = self.calculate(data, params)
        entries = (data['close'] > poc_data['poc']) & (data['close'].shift(1) <= poc_data['poc'].shift(1))
        exits = (data['close'] < poc_data['poc']) & (data['close'].shift(1) >= poc_data['poc'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('poc_cross_down', index=data.index),
                'signal_strength': abs(poc_data['distance_poc'])}
    
    def get_ml_features(self, data, params):
        poc_data = self.calculate(data, params)
        return pd.DataFrame({
            'poc': poc_data['poc'],
            'poc_volume': poc_data['poc_volume'],
            'distance_poc': poc_data['distance_poc'],
            'above_poc': poc_data['above_poc'],
            'poc_change': poc_data['poc_change'],
            'poc_trend': poc_data['poc_trend']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
