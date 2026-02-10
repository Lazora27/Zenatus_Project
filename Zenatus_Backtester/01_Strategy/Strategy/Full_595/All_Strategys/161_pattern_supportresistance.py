"""161 - Support & Resistance Levels"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SupportResistance:
    """Support & Resistance - Dynamic S/R level detection"""
    PARAMETERS = {
        'lookback': {'default': 50, 'values': [30,40,50,60], 'optimize': True},
        'num_levels': {'default': 3, 'values': [2,3,4,5], 'optimize': True},
        'proximity': {'default': 0.002, 'values': [0.001,0.002,0.003], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SupportResistance", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 50)
        num_levels = params.get('num_levels', 3)
        proximity = params.get('proximity', 0.002)
        
        # Find pivot points
        pivot_high = (data['high'] > data['high'].shift(1)) & (data['high'] > data['high'].shift(-1))
        pivot_low = (data['low'] < data['low'].shift(1)) & (data['low'] < data['low'].shift(-1))
        
        # Calculate S/R levels
        resistance_levels = pd.DataFrame(index=data.index)
        support_levels = pd.DataFrame(index=data.index)
        
        for i in range(lookback, len(data)):
            # Get recent pivots
            recent_highs = data['high'].iloc[i-lookback:i][pivot_high.iloc[i-lookback:i]]
            recent_lows = data['low'].iloc[i-lookback:i][pivot_low.iloc[i-lookback:i]]
            
            # Cluster pivots to find levels
            if len(recent_highs) > 0:
                # Sort and find clusters
                sorted_highs = sorted(recent_highs.values, reverse=True)
                res_levels = []
                
                for high in sorted_highs:
                    # Check if this high is close to existing level
                    is_new = True
                    for level in res_levels:
                        if abs(high - level) / level < proximity:
                            is_new = False
                            break
                    
                    if is_new:
                        res_levels.append(high)
                        if len(res_levels) >= num_levels:
                            break
                
                # Store levels
                for j, level in enumerate(res_levels[:num_levels]):
                    resistance_levels.loc[data.index[i], f'R{j+1}'] = level
            
            if len(recent_lows) > 0:
                sorted_lows = sorted(recent_lows.values)
                sup_levels = []
                
                for low in sorted_lows:
                    is_new = True
                    for level in sup_levels:
                        if abs(low - level) / level < proximity:
                            is_new = False
                            break
                    
                    if is_new:
                        sup_levels.append(low)
                        if len(sup_levels) >= num_levels:
                            break
                
                for j, level in enumerate(sup_levels[:num_levels]):
                    support_levels.loc[data.index[i], f'S{j+1}'] = level
        
        # Fill forward
        resistance_levels = resistance_levels.fillna(method='ffill')
        support_levels = support_levels.fillna(method='ffill')
        
        # Nearest levels
        nearest_resistance = resistance_levels.min(axis=1)
        nearest_support = support_levels.max(axis=1)
        
        # Distance to levels
        dist_to_resistance = (nearest_resistance - data['close']) / data['close']
        dist_to_support = (data['close'] - nearest_support) / data['close']
        
        # Signal: near support = bullish, near resistance = bearish
        signal = pd.Series(0, index=data.index)
        signal[dist_to_support < proximity] = 1  # Near support
        signal[dist_to_resistance < proximity] = -1  # Near resistance
        
        return pd.DataFrame({
            'signal': signal,
            'nearest_resistance': nearest_resistance,
            'nearest_support': nearest_support,
            'dist_resistance': dist_to_resistance,
            'dist_support': dist_to_support
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        sr = self.calculate(data, params)
        # Entry near support
        entries = (sr['signal'] == 1)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 
                'signal_strength': abs(sr['signal'])}
    
    def generate_signals_dynamic(self, data, params):
        sr = self.calculate(data, params)
        entries = (sr['signal'] == 1)
        exits = (sr['signal'] == -1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('near_resistance', index=data.index),
                'signal_strength': abs(sr['signal'])}
    
    def get_ml_features(self, data, params):
        sr = self.calculate(data, params)
        return pd.DataFrame({
            'sr_signal': sr['signal'],
            'sr_dist_res': sr['dist_resistance'],
            'sr_dist_sup': sr['dist_support'],
            'sr_near_support': (sr['signal'] == 1).astype(int),
            'sr_near_resistance': (sr['signal'] == -1).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
