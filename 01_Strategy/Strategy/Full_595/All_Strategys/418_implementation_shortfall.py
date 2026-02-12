"""418 - Implementation Shortfall"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ImplementationShortfall:
    """Implementation Shortfall - Total execution cost breakdown"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ImplementationShortfall", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Benchmark price (open)
        benchmark = data['open']
        
        # Execution price (close)
        execution = data['close']
        
        # Total shortfall
        total_shortfall = execution - benchmark
        
        # Decompose into components:
        # 1. Delay cost (decision to execution)
        delay_cost = data['close'] - data['open']
        
        # 2. Market impact (price moved during execution)
        market_impact = (data['high'] - data['low']) / 2
        
        # 3. Timing cost (opportunity cost)
        timing_cost = total_shortfall - delay_cost - market_impact
        
        # Relative costs
        relative_total = total_shortfall / benchmark
        relative_delay = delay_cost / benchmark
        relative_impact = market_impact / benchmark
        
        # Average costs
        avg_total_cost = relative_total.rolling(period).mean()
        avg_delay_cost = relative_delay.rolling(period).mean()
        avg_impact_cost = relative_impact.rolling(period).mean()
        
        # Execution efficiency (low cost = good)
        efficiency = 1 / (abs(avg_total_cost) + 1e-10)
        efficiency_normalized = efficiency / efficiency.rolling(50).max()
        
        # Smooth
        efficiency_smooth = efficiency_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'total_shortfall': total_shortfall,
            'delay_cost': delay_cost,
            'market_impact': market_impact,
            'timing_cost': timing_cost,
            'relative_total': relative_total,
            'avg_total_cost': avg_total_cost,
            'avg_delay_cost': avg_delay_cost,
            'avg_impact_cost': avg_impact_cost,
            'efficiency': efficiency_normalized,
            'efficiency_smooth': efficiency_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High efficiency
        entries = result['efficiency_smooth'] > 0.6
        
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
            'signal_strength': result['efficiency_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Efficient
        entries = result['efficiency'] > 0.6
        
        # Exit: Inefficient
        exits = result['efficiency'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_cost', index=data.index),
            'signal_strength': result['efficiency_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['impl_total_shortfall'] = result['total_shortfall']
        features['impl_delay_cost'] = result['delay_cost']
        features['impl_market_impact'] = result['market_impact']
        features['impl_timing_cost'] = result['timing_cost']
        features['impl_relative_total'] = result['relative_total']
        features['impl_avg_total_cost'] = result['avg_total_cost']
        features['impl_avg_delay_cost'] = result['avg_delay_cost']
        features['impl_avg_impact_cost'] = result['avg_impact_cost']
        features['impl_efficiency'] = result['efficiency']
        features['impl_efficiency_smooth'] = result['efficiency_smooth']
        features['impl_efficient'] = (result['efficiency'] > 0.6).astype(int)
        
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

