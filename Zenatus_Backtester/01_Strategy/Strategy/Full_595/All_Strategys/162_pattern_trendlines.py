"""162 - Trendline Detector"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Trendlines:
    """Trendline Detector - Automatic trendline detection and breaks"""
    PARAMETERS = {
        'lookback': {'default': 50, 'values': [30,40,50,60], 'optimize': True},
        'min_touches': {'default': 2, 'values': [2,3], 'optimize': True},
        'tolerance': {'default': 0.01, 'values': [0.005,0.01,0.015], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Trendlines", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 50)
        min_touches = params.get('min_touches', 2)
        tolerance = params.get('tolerance', 0.01)
        
        # Find swing points
        swing_high = (data['high'] > data['high'].shift(1)) & (data['high'] > data['high'].shift(-1))
        swing_low = (data['low'] < data['low'].shift(1)) & (data['low'] < data['low'].shift(-1))
        
        # Trendline values
        uptrend_line = pd.Series(np.nan, index=data.index)
        downtrend_line = pd.Series(np.nan, index=data.index)
        
        for i in range(lookback, len(data)):
            # Get recent swing lows for uptrend
            recent_lows_idx = data.index[i-lookback:i][swing_low.iloc[i-lookback:i]]
            
            if len(recent_lows_idx) >= min_touches:
                # Try to fit a line through swing lows
                lows = data.loc[recent_lows_idx, 'low'].values
                x = np.arange(len(lows))
                
                # Linear regression
                if len(x) > 1:
                    slope, intercept = np.polyfit(x, lows, 1)
                    
                    # Check if line is valid (upward sloping)
                    if slope > 0:
                        # Count touches
                        touches = 0
                        for j, low in enumerate(lows):
                            line_value = slope * j + intercept
                            if abs(low - line_value) / line_value < tolerance:
                                touches += 1
                        
                        if touches >= min_touches:
                            # Project to current bar
                            uptrend_line.iloc[i] = slope * len(lows) + intercept
            
            # Get recent swing highs for downtrend
            recent_highs_idx = data.index[i-lookback:i][swing_high.iloc[i-lookback:i]]
            
            if len(recent_highs_idx) >= min_touches:
                highs = data.loc[recent_highs_idx, 'high'].values
                x = np.arange(len(highs))
                
                if len(x) > 1:
                    slope, intercept = np.polyfit(x, highs, 1)
                    
                    # Check if line is valid (downward sloping)
                    if slope < 0:
                        touches = 0
                        for j, high in enumerate(highs):
                            line_value = slope * j + intercept
                            if abs(high - line_value) / line_value < tolerance:
                                touches += 1
                        
                        if touches >= min_touches:
                            downtrend_line.iloc[i] = slope * len(highs) + intercept
        
        # Fill forward
        uptrend_line = uptrend_line.fillna(method='ffill')
        downtrend_line = downtrend_line.fillna(method='ffill')
        
        # Detect breaks
        uptrend_break = (data['close'] > uptrend_line) & (data['close'].shift(1) <= uptrend_line.shift(1))
        downtrend_break = (data['close'] < downtrend_line) & (data['close'].shift(1) >= downtrend_line.shift(1))
        
        signal = pd.Series(0, index=data.index)
        signal[uptrend_break] = 1
        signal[downtrend_break] = -1
        
        return pd.DataFrame({
            'signal': signal,
            'uptrend_line': uptrend_line,
            'downtrend_line': downtrend_line,
            'uptrend_break': uptrend_break.astype(int),
            'downtrend_break': downtrend_break.astype(int)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        tl = self.calculate(data, params)
        # Entry on uptrend break
        entries = (tl['signal'] == 1)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(tl['signal'])}
    
    def generate_signals_dynamic(self, data, params):
        tl = self.calculate(data, params)
        entries = (tl['signal'] == 1)
        exits = (tl['signal'] == -1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('downtrend_break', index=data.index),
                'signal_strength': abs(tl['signal'])}
    
    def get_ml_features(self, data, params):
        tl = self.calculate(data, params)
        return pd.DataFrame({
            'tl_signal': tl['signal'],
            'tl_uptrend_break': tl['uptrend_break'],
            'tl_downtrend_break': tl['downtrend_break'],
            'tl_dist_up': (data['close'] - tl['uptrend_line']) / data['close'],
            'tl_dist_down': (tl['downtrend_line'] - data['close']) / data['close']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
