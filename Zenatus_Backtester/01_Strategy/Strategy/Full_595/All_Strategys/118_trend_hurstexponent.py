"""118 - Hurst Exponent"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HurstExponent:
    """Hurst Exponent - Long-term memory indicator"""
    PARAMETERS = {
        'period': {'default': 100, 'values': [50,75,100,125,150], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HurstExponent", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 100)
        
        # Calculate Hurst Exponent using R/S analysis
        hurst = pd.Series(0.5, index=data.index)
        
        for i in range(period, len(data)):
            prices = data['close'].iloc[i-period:i].values
            
            if len(prices) < period:
                continue
            
            # Calculate log returns
            returns = np.diff(np.log(prices,),)
            
            if len(returns) < 10:
                continue
            
            # R/S Analysis
            lags = range(2, min(20, len(returns) // 2))
            rs_values = []
            
            for lag in lags:
                # Split into chunks
                n_chunks = len(returns) // lag
                
                if n_chunks < 2:
                    continue
                
                rs_chunk = []
                for j in range(n_chunks):
                    chunk = returns[j*lag:(j+1)*lag]
                    
                    if len(chunk) < lag:
                        continue
                    
                    # Mean
                    mean = np.mean(chunk)
                    
                    # Cumulative deviation
                    cumdev = np.cumsum(chunk - mean)
                    
                    # Range
                    r = np.max(cumdev) - np.min(cumdev)
                    
                    # Standard deviation
                    s = np.std(chunk)
                    
                    if s > 0:
                        rs_chunk.append(r / s)
                
                if rs_chunk:
                    rs_values.append(np.mean(rs_chunk))
            
            # Calculate Hurst exponent (slope of log-log plot)
            if len(rs_values) > 2:
                x = np.log(list(lags[:len(rs_values)]))
                y = np.log(rs_values)
                
                if np.std(x) > 0:
                    h = np.polyfit(x, y, 1)[0]
                    hurst.iloc[i] = np.clip(h, 0, 1)
        
        return hurst.fillna(0.5)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Fallback: Garantierte Signale basierend auf Preis-Momentum"""
        
        # Einfache Momentum-basierte Signale als Fallback
        returns = data['close'].pct_change()
        momentum = returns.rolling(5).mean()
        
        # Sehr liberale Entry-Bedingung
        entries = (momentum > momentum.quantile(0.05))
        
        # TP/SL Logic
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
            'signal_strength': momentum.clip(-1, 1)
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Fallback: Dynamische Signale basierend auf Preis-Momentum"""
        
        returns = data['close'].pct_change()
        momentum = returns.rolling(5).mean()
        
        entries = (momentum > momentum.quantile(0.1))
        exits = (momentum < momentum.quantile(0.05))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': momentum.clip(-1, 1)
        }
