"""159 - Elliott Wave Detector"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ElliottWave:
    """Elliott Wave Detector - Simplified Elliott Wave identification"""
    PARAMETERS = {
        'lookback': {'default': 50, 'values': [30,40,50,60], 'optimize': True},
        'wave_tolerance': {'default': 0.1, 'values': [0.05,0.1,0.15], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ElliottWave", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 50)
        tolerance = params.get('wave_tolerance', 0.1)
        
        # Find swing points
        swing_high = (data['high'] > data['high'].shift(1)) & (data['high'] > data['high'].shift(-1))
        swing_low = (data['low'] < data['low'].shift(1)) & (data['low'] < data['low'].shift(-1))
        
        # Elliott Wave states
        wave_count = pd.Series(0, index=data.index)
        wave_direction = pd.Series(0, index=data.index)  # 1=impulse up, -1=impulse down
        
        # Simplified wave detection
        for i in range(lookback, len(data)):
            window_highs = data['high'].iloc[i-lookback:i][swing_high.iloc[i-lookback:i]]
            window_lows = data['low'].iloc[i-lookback:i][swing_low.iloc[i-lookback:i]]
            
            # Need at least 5 swings for a complete wave
            if len(window_highs) >= 3 and len(window_lows) >= 2:
                # Bullish impulse: 5 waves (1-up, 2-down, 3-up, 4-down, 5-up)
                # Simplified: check for alternating highs and lows
                
                recent_highs = window_highs.iloc[-3:].values
                recent_lows = window_lows.iloc[-2:].values
                
                # Wave 1-2-3 pattern (simplified)
                if len(recent_highs) >= 2 and len(recent_lows) >= 1:
                    wave1 = recent_highs[0]
                    wave2 = recent_lows[0]
                    wave3 = recent_highs[1]
                    
                    # Wave 3 should be higher than wave 1
                    if wave3 > wave1:
                        # Wave 2 should not retrace more than 100% of wave 1
                        if wave2 > (wave1 - (wave1 - window_lows.iloc[0])):
                            wave_count.iloc[i] = 3
                            wave_direction.iloc[i] = 1
                
                # Check for wave 5 completion
                if len(recent_highs) >= 3:
                    wave5 = recent_highs[2]
                    if wave5 > wave3:
                        wave_count.iloc[i] = 5
                        wave_direction.iloc[i] = 1
        
        # Wave position indicator
        wave_position = wave_count * wave_direction
        
        return pd.DataFrame({
            'wave_count': wave_count,
            'wave_direction': wave_direction,
            'wave_position': wave_position
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        ew = self.calculate(data, params)
        # Entry at wave 3 or wave 5
        entries = ((ew['wave_count'] == 3) | (ew['wave_count'] == 5)) & (ew['wave_direction'] == 1)
        
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
                'signal_strength': (ew['wave_count'] / 5).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        ew = self.calculate(data, params)
        entries = ((ew['wave_count'] == 3) | (ew['wave_count'] == 5)) & (ew['wave_direction'] == 1)
        exits = (ew['wave_count'] == 5) & (ew['wave_direction'] == -1)  # Reversal
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('wave_reversal', index=data.index),
                'signal_strength': (ew['wave_count'] / 5).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        ew = self.calculate(data, params)
        return pd.DataFrame({
            'ew_count': ew['wave_count'],
            'ew_direction': ew['wave_direction'],
            'ew_position': ew['wave_position'],
            'ew_wave3': (ew['wave_count'] == 3).astype(int),
            'ew_wave5': (ew['wave_count'] == 5).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
