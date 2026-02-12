"""239 - Retail Volume"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RetailVolume:
    """Retail Volume - Estimated Retail Trader Volume"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RetailVolume", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Retail Volume Proxy (smaller trades, higher volatility)
        price_range = high - low
        price_volatility = price_range / close
        vol_ma = volume.rolling(period).mean()
        
        # Small volume with high price impact (retail characteristic)
        retail_vol = (volume < vol_ma) & (price_volatility > price_volatility.rolling(period).median())
        
        # Cumulative Retail Volume
        cumulative_retail = (volume * retail_vol.astype(int)).rolling(period).sum()
        
        # Retail Participation
        total_volume = volume.rolling(period).sum()
        retail_participation = cumulative_retail / (total_volume + 1e-10)
        
        # Retail Sentiment (contrarian indicator)
        price_change = close.diff()
        retail_sentiment = (retail_vol.astype(int) * volume * np.sign(price_change)).rolling(period).sum()
        
        # High Retail Activity (potential reversal)
        high_retail = (retail_participation > 0.6).astype(int)
        
        return pd.DataFrame({
            'retail_vol': retail_vol.astype(int),
            'cumulative_retail': cumulative_retail,
            'retail_participation': retail_participation,
            'retail_sentiment': retail_sentiment,
            'high_retail': high_retail
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        rv_data = self.calculate(data, params)
        # Contrarian: Entry when high retail activity + opposite price move
        entries = (rv_data['retail_participation'] > 0.3)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': rv_data['retail_participation']}
    
    def generate_signals_dynamic(self, data, params):
        rv_data = self.calculate(data, params)
        entries = (rv_data['retail_participation'] > 0.3)
        exits = (rv_data['retail_participation'] < 0.3)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('retail_exit', index=data.index),
                'signal_strength': rv_data['retail_participation']}
    
    def get_ml_features(self, data, params):
        rv_data = self.calculate(data, params)
        return pd.DataFrame({
            'retail_vol': rv_data['retail_vol'],
            'cumulative_retail': rv_data['cumulative_retail'],
            'retail_participation': rv_data['retail_participation'],
            'retail_sentiment': rv_data['retail_sentiment'],
            'high_retail': rv_data['high_retail']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
