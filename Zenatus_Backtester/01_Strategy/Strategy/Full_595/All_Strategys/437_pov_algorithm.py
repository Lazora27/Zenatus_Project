"""437 - Percentage of Volume (POV) Algorithm"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_POVAlgorithm:
    """POV Algorithm - Percentage of Volume execution strategy"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'target_pov': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2,0.25,0.3], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "POVAlgorithm", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        target_pov = params.get('target_pov', 0.1)
        
        # Volume metrics
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_std = volume.rolling(period).std()
        
        # POV participation rate
        participation_rate = volume / (avg_volume + 1e-10)
        
        # Target POV achievement
        pov_target = target_pov
        pov_actual = participation_rate * target_pov
        pov_deviation = abs(pov_actual - pov_target)
        
        # Volume predictability (for POV execution)
        volume_cv = volume_std / (avg_volume + 1e-10)  # Coefficient of variation
        predictability = 1 / (volume_cv + 1e-10)
        predictability_normalized = predictability / predictability.rolling(50).max()
        
        # Execution quality
        price_impact = abs(data['close'] - data['open']) / data['open']
        avg_impact = price_impact.rolling(period).mean()
        
        # POV execution score (high predictability, low impact)
        pov_score = predictability_normalized * (1 - avg_impact)
        pov_score_smooth = pov_score.rolling(5).mean()
        
        # Optimal execution window
        optimal_window = (predictability_normalized > 0.6) & (avg_impact < 0.001)
        
        # Cumulative volume tracking
        cumulative_volume = volume.rolling(period).sum()
        volume_acceleration = volume.diff() / (volume.shift(1) + 1e-10)
        
        # POV efficiency
        efficiency = pov_score / (pov_deviation + 1e-10)
        efficiency_normalized = efficiency / efficiency.rolling(50).max()
        
        return pd.DataFrame({
            'avg_volume': avg_volume,
            'volume_std': volume_std,
            'participation_rate': participation_rate,
            'pov_actual': pov_actual,
            'pov_deviation': pov_deviation,
            'volume_cv': volume_cv,
            'predictability': predictability_normalized,
            'price_impact': price_impact,
            'avg_impact': avg_impact,
            'pov_score': pov_score,
            'pov_score_smooth': pov_score_smooth,
            'optimal_window': optimal_window.astype(int),
            'cumulative_volume': cumulative_volume,
            'volume_acceleration': volume_acceleration,
            'efficiency': efficiency_normalized
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal POV execution window
        entries = (result['pov_score_smooth'] > 0.6) & (result['optimal_window'] == 1)
        
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
            'signal_strength': result['pov_score_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal window
        entries = result['optimal_window'] == 1
        
        # Exit: Poor execution conditions
        exits = (result['predictability'] < 0.4) | (result['avg_impact'] > 0.002)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('poor_pov_conditions', index=data.index),
            'signal_strength': result['pov_score_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['pov_avg_volume'] = result['avg_volume']
        features['pov_volume_std'] = result['volume_std']
        features['pov_participation_rate'] = result['participation_rate']
        features['pov_actual'] = result['pov_actual']
        features['pov_deviation'] = result['pov_deviation']
        features['pov_volume_cv'] = result['volume_cv']
        features['pov_predictability'] = result['predictability']
        features['pov_price_impact'] = result['price_impact']
        features['pov_avg_impact'] = result['avg_impact']
        features['pov_score'] = result['pov_score']
        features['pov_score_smooth'] = result['pov_score_smooth']
        features['pov_optimal_window'] = result['optimal_window']
        features['pov_cumulative_volume'] = result['cumulative_volume']
        features['pov_volume_acceleration'] = result['volume_acceleration']
        features['pov_efficiency'] = result['efficiency']
        
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

