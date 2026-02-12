"""330 - Consensus Aggregator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ConsensusAggregator:
    """Consensus Aggregator - Aggregates signals from multiple sources"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'consensus_threshold': {'default': 0.7, 'values': [0.6,0.65,0.7,0.75,0.8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ConsensusAggregator", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('consensus_threshold', 0.7)
        
        # Collect signals from multiple sources
        signals = []
        
        # Signal 1: Moving Average
        sma = data['close'].rolling(period).mean()
        signals.append((data['close'] > sma).astype(int))
        
        # Signal 2: RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        signals.append((rsi > 30).astype(int) & (rsi < 70).astype(int))
        
        # Signal 3: MACD
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signals.append((macd > 0).astype(int))
        
        # Signal 4: Bollinger Bands
        bb_std = data['close'].rolling(period).std()
        bb_upper = sma + 2 * bb_std
        bb_lower = sma - 2 * bb_std
        signals.append((data['close'] > bb_lower).astype(int) & (data['close'] < bb_upper).astype(int))
        
        # Signal 5: Volume
        vol_ma = data['volume'].rolling(period).mean()
        signals.append((data['volume'] > vol_ma * 0.7).astype(int))
        
        # Signal 6: ADX (trend strength)
        high_low = data['high'] - data['low']
        tr = high_low.rolling(period).mean()
        plus_dm = (data['high'] - data['high'].shift(1)).clip(lower=0)
        adx_signal = plus_dm.rolling(period).mean() / (tr + 1e-10)
        signals.append((adx_signal > 0.2).astype(int))
        
        # Signal 7: Stochastic
        low_min = data['low'].rolling(period).min()
        high_max = data['high'].rolling(period).max()
        stoch = (data['close'] - low_min) / (high_max - low_min + 1e-10) * 100
        signals.append((stoch > 20).astype(int) & (stoch < 80).astype(int))
        
        # Aggregate signals
        signals_df = pd.concat(signals, axis=1)
        consensus_score = signals_df.mean(axis=1)
        
        # Strong consensus
        strong_consensus = consensus_score > threshold
        
        # Consensus strength
        consensus_strength = abs(consensus_score - 0.5) * 2
        
        return pd.DataFrame({
            'consensus_score': consensus_score,
            'strong_consensus': strong_consensus.astype(int),
            'consensus_strength': consensus_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong consensus
        entries = result['strong_consensus'] == 1
        
        # Manual TP/SL
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': result['consensus_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong consensus
        entries = result['strong_consensus'] == 1
        
        # Exit: Consensus breaks
        exits = result['consensus_score'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('consensus_break', index=data.index),
            'signal_strength': result['consensus_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['consensus_score'] = result['consensus_score']
        features['consensus_strong'] = result['strong_consensus']
        features['consensus_strength'] = result['consensus_strength']
        features['consensus_very_strong'] = (result['consensus_score'] > 0.8).astype(int)
        features['consensus_weak'] = (result['consensus_score'] < 0.4).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass

    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100, 150],
            'sl_pips': [15, 25, 35, 50, 75]
        }

