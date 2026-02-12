"""157 - Chart Patterns (Triangles, Flags, H&S)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ChartPatterns:
    """Chart Patterns - Detects triangles, flags, head & shoulders"""
    PARAMETERS = {
        'lookback': {'default': 30, 'values': [20,30,40,50], 'optimize': True},
        'tolerance': {'default': 0.02, 'values': [0.01,0.02,0.03], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ChartPatterns", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 30)
        tolerance = params.get('tolerance', 0.02)
        
        # Find swing highs and lows
        swing_high = (data['high'] > data['high'].shift(1)) & (data['high'] > data['high'].shift(-1))
        swing_low = (data['low'] < data['low'].shift(1)) & (data['low'] < data['low'].shift(-1))
        
        patterns = pd.DataFrame(index=data.index)
        
        # 1. Ascending Triangle (flat top, rising bottom)
        patterns['ascending_triangle'] = pd.Series(0, index=data.index)
        
        # 2. Descending Triangle (flat bottom, falling top)
        patterns['descending_triangle'] = pd.Series(0, index=data.index)
        
        # 3. Bull Flag (consolidation after uptrend)
        patterns['bull_flag'] = pd.Series(0, index=data.index)
        
        # 4. Bear Flag (consolidation after downtrend)
        patterns['bear_flag'] = pd.Series(0, index=data.index)
        
        for i in range(lookback, len(data)):
            window = data.iloc[i-lookback:i]
            
            # Bull Flag: strong uptrend followed by tight consolidation
            uptrend = window['close'].iloc[-1] > window['close'].iloc[0] * 1.02
            consolidation = window['high'].iloc[-10:].std() / window['close'].iloc[-10:].mean() < 0.01
            
            if uptrend and consolidation:
                patterns['bull_flag'].iloc[i] = 1
            
            # Bear Flag: strong downtrend followed by tight consolidation
            downtrend = window['close'].iloc[-1] < window['close'].iloc[0] * 0.98
            
            if downtrend and consolidation:
                patterns['bear_flag'].iloc[i] = 1
            
            # Ascending Triangle: resistance level with rising support
            highs = window['high'].iloc[-20:]
            resistance_level = highs.max()
            near_resistance = (highs > resistance_level * (1 - tolerance)).sum() >= 2
            
            lows = window['low'].iloc[-20:]
            rising_lows = (lows.iloc[-10:].mean() > lows.iloc[:10].mean())
            
            if near_resistance and rising_lows:
                patterns['ascending_triangle'].iloc[i] = 1
            
            # Descending Triangle: support level with falling resistance
            support_level = lows.min()
            near_support = (lows < support_level * (1 + tolerance)).sum() >= 2
            
            highs = window['high'].iloc[-20:]
            falling_highs = (highs.iloc[-10:].mean() < highs.iloc[:10].mean())
            
            if near_support and falling_highs:
                patterns['descending_triangle'].iloc[i] = 1
        
        # Composite signal
        bullish_score = patterns['ascending_triangle'] + patterns['bull_flag']
        bearish_score = patterns['descending_triangle'] + patterns['bear_flag']
        signal = bullish_score - bearish_score
        
        return pd.DataFrame({
            'signal': signal,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            **patterns
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        cp = self.calculate(data, params)
        # Entry on bullish pattern
        entries = (cp['signal'] > 0)
        
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
                'signal_strength': abs(cp['signal']).clip(0, 2) / 2}
    
    def generate_signals_dynamic(self, data, params):
        cp = self.calculate(data, params)
        entries = (cp['signal'] > 0)
        exits = (cp['signal'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_pattern', index=data.index),
                'signal_strength': abs(cp['signal']).clip(0, 2) / 2}
    
    def get_ml_features(self, data, params):
        cp = self.calculate(data, params)
        return pd.DataFrame({
            'chart_signal': cp['signal'],
            'chart_asc_triangle': cp['ascending_triangle'],
            'chart_desc_triangle': cp['descending_triangle'],
            'chart_bull_flag': cp['bull_flag'],
            'chart_bear_flag': cp['bear_flag']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
