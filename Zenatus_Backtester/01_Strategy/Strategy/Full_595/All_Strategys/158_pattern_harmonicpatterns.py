"""158 - Harmonic Patterns (Gartley, Butterfly, Bat)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HarmonicPatterns:
    """Harmonic Patterns - Fibonacci-based harmonic patterns"""
    PARAMETERS = {
        'lookback': {'default': 50, 'values': [30,40,50,60], 'optimize': True},
        'tolerance': {'default': 0.05, 'values': [0.03,0.05,0.07], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HarmonicPatterns", "Pattern", __version__
    
    def check_ratio(self, value, target, tolerance):
        """Check if value is within tolerance of target ratio"""
        return abs(value - target) / target < tolerance
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 50)
        tolerance = params.get('tolerance', 0.05)
        
        # Find swing points
        swing_high = (data['high'] > data['high'].shift(1)) & (data['high'] > data['high'].shift(-1))
        swing_low = (data['low'] < data['low'].shift(1)) & (data['low'] < data['low'].shift(-1))
        
        patterns = pd.DataFrame(index=data.index)
        patterns['gartley_bull'] = 0
        patterns['gartley_bear'] = 0
        patterns['butterfly_bull'] = 0
        patterns['butterfly_bear'] = 0
        patterns['bat_bull'] = 0
        patterns['bat_bear'] = 0
        
        # Simplified harmonic detection (XABCD pattern)
        for i in range(lookback, len(data)):
            window_highs = data['high'].iloc[i-lookback:i][swing_high.iloc[i-lookback:i]]
            window_lows = data['low'].iloc[i-lookback:i][swing_low.iloc[i-lookback:i]]
            
            if len(window_highs) >= 3 and len(window_lows) >= 2:
                # Bullish Gartley pattern (simplified)
                # X-A-B-C-D with specific Fibonacci ratios
                # AB = 0.618 of XA, BC = 0.382-0.886 of AB, CD = 1.272-1.618 of BC
                
                X = window_lows.iloc[-5] if len(window_lows) >= 5 else window_lows.iloc[0]
                A = window_highs.iloc[-3] if len(window_highs) >= 3 else window_highs.iloc[0]
                B = window_lows.iloc[-3] if len(window_lows) >= 3 else window_lows.iloc[-1]
                C = window_highs.iloc[-2] if len(window_highs) >= 2 else window_highs.iloc[-1]
                D = data['low'].iloc[i]
                
                XA = A - X
                AB = A - B
                BC = C - B
                CD = C - D
                
                if XA > 0:
                    ab_ratio = AB / XA
                    if AB > 0:
                        bc_ratio = BC / AB
                        cd_ratio = CD / BC if BC > 0 else 0
                        
                        # Gartley: AB=0.618XA, BC=0.382-0.886AB, CD=1.272-1.618BC
                        if self.check_ratio(ab_ratio, 0.618, tolerance):
                            if 0.382 <= bc_ratio <= 0.886:
                                if 1.272 <= cd_ratio <= 1.618:
                                    patterns['gartley_bull'].iloc[i] = 1
                        
                        # Butterfly: AB=0.786XA, BC=0.382-0.886AB, CD=1.618-2.618BC
                        if self.check_ratio(ab_ratio, 0.786, tolerance):
                            if 0.382 <= bc_ratio <= 0.886:
                                if 1.618 <= cd_ratio <= 2.618:
                                    patterns['butterfly_bull'].iloc[i] = 1
                        
                        # Bat: AB=0.382-0.5XA, BC=0.382-0.886AB, CD=1.618-2.618BC
                        if 0.382 <= ab_ratio <= 0.5:
                            if 0.382 <= bc_ratio <= 0.886:
                                if 1.618 <= cd_ratio <= 2.618:
                                    patterns['bat_bull'].iloc[i] = 1
        
        # Composite signal
        bullish_score = patterns['gartley_bull'] + patterns['butterfly_bull'] + patterns['bat_bull']
        bearish_score = patterns['gartley_bear'] + patterns['butterfly_bear'] + patterns['bat_bear']
        signal = bullish_score - bearish_score
        
        return pd.DataFrame({
            'signal': signal,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            **patterns
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        hp = self.calculate(data, params)
        # Entry on bullish harmonic
        entries = (hp['signal'] > 0)
        
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
                'signal_strength': abs(hp['signal']).clip(0, 3) / 3}
    
    def generate_signals_dynamic(self, data, params):
        hp = self.calculate(data, params)
        entries = (hp['signal'] > 0)
        exits = (hp['signal'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_harmonic', index=data.index),
                'signal_strength': abs(hp['signal']).clip(0, 3) / 3}
    
    def get_ml_features(self, data, params):
        hp = self.calculate(data, params)
        return pd.DataFrame({
            'harmonic_signal': hp['signal'],
            'harmonic_gartley': hp['gartley_bull'],
            'harmonic_butterfly': hp['butterfly_bull'],
            'harmonic_bat': hp['bat_bull'],
            'harmonic_any': (hp['bullish_score'] > 0).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
