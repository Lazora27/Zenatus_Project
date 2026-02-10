"""453 - Effective Tick Size Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_EffectiveTickSize:
    """Effective Tick Size - Measures actual price granularity and constraints"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "EffectiveTickSize", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Effective tick size analysis
        
        # 1. Observed price changes
        price_change = data['close'].diff()
        abs_price_change = abs(price_change)
        
        # 2. Minimum non-zero price change (effective tick)
        min_price_change = abs_price_change[abs_price_change > 0].rolling(period).min()
        
        # 3. Median price change (typical tick)
        median_price_change = abs_price_change[abs_price_change > 0].rolling(period).median()
        
        # 4. Price change distribution
        price_change_std = abs_price_change.rolling(period).std()
        
        # 5. Tick size ratio (actual vs nominal)
        nominal_tick = 0.0001  # Forex pip
        tick_size_ratio = median_price_change / nominal_tick
        
        # 6. Price clustering at ticks
        price_mod = (data['close'] % nominal_tick) / nominal_tick
        clustering_score = (abs(price_mod) < 0.1).astype(int).rolling(period).mean()
        
        # 7. Effective spread (in ticks)
        spread = data['high'] - data['low']
        effective_spread_ticks = spread / (median_price_change + 1e-10)
        
        # 8. Tick constraint score
        # High clustering + large tick ratio = constrained
        constraint_score = clustering_score * tick_size_ratio
        constraint_score_normalized = constraint_score / constraint_score.rolling(50).max()
        constraint_score_smooth = constraint_score_normalized.rolling(5).mean()
        
        # 9. Price granularity
        # More unique price levels = better granularity
        unique_prices = data['close'].rolling(period).apply(
            lambda x: len(x.unique()) / len(x) if len(x) > 0 else 0,
            raw=False
        )
        granularity = unique_prices
        
        # 10. Trading flexibility
        # Low constraint + high granularity = flexible
        flexibility = granularity * (1 - constraint_score_smooth)
        flexibility_smooth = flexibility.rolling(5).mean()
        
        # 11. High constraint periods
        high_constraint = constraint_score_smooth > 0.6
        
        # 12. Optimal trading conditions
        optimal_conditions = (constraint_score_smooth < 0.4) & (flexibility_smooth > 0.5)
        
        # 13. Tick size efficiency
        # Ratio of actual to theoretical optimal tick size
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        
        # Optimal tick = balances liquidity and precision
        theoretical_optimal = spread / np.sqrt(avg_volume + 1e-10)
        tick_efficiency = median_price_change / (theoretical_optimal + 1e-10)
        tick_efficiency_normalized = tick_efficiency / tick_efficiency.rolling(50).max()
        
        return pd.DataFrame({
            'abs_price_change': abs_price_change,
            'min_price_change': min_price_change,
            'median_price_change': median_price_change,
            'price_change_std': price_change_std,
            'tick_size_ratio': tick_size_ratio,
            'price_mod': price_mod,
            'clustering_score': clustering_score,
            'spread': spread,
            'effective_spread_ticks': effective_spread_ticks,
            'constraint_score': constraint_score_normalized,
            'constraint_score_smooth': constraint_score_smooth,
            'unique_prices': unique_prices,
            'granularity': granularity,
            'flexibility': flexibility,
            'flexibility_smooth': flexibility_smooth,
            'high_constraint': high_constraint.astype(int),
            'optimal_conditions': optimal_conditions.astype(int),
            'theoretical_optimal': theoretical_optimal,
            'tick_efficiency': tick_efficiency_normalized
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions (low constraint, high flexibility)
        entries = (result['optimal_conditions'] == 1) & (result['flexibility_smooth'] > 0.6)
        
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
            'signal_strength': result['flexibility_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions
        entries = result['optimal_conditions'] == 1
        
        # Exit: High constraint
        exits = result['high_constraint'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_tick_constraint', index=data.index),
            'signal_strength': result['flexibility_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ets_abs_price_change'] = result['abs_price_change']
        features['ets_min_price_change'] = result['min_price_change']
        features['ets_median_price_change'] = result['median_price_change']
        features['ets_price_change_std'] = result['price_change_std']
        features['ets_tick_size_ratio'] = result['tick_size_ratio']
        features['ets_price_mod'] = result['price_mod']
        features['ets_clustering_score'] = result['clustering_score']
        features['ets_spread'] = result['spread']
        features['ets_effective_spread_ticks'] = result['effective_spread_ticks']
        features['ets_constraint_score'] = result['constraint_score']
        features['ets_constraint_score_smooth'] = result['constraint_score_smooth']
        features['ets_unique_prices'] = result['unique_prices']
        features['ets_granularity'] = result['granularity']
        features['ets_flexibility'] = result['flexibility']
        features['ets_flexibility_smooth'] = result['flexibility_smooth']
        features['ets_high_constraint'] = result['high_constraint']
        features['ets_optimal_conditions'] = result['optimal_conditions']
        features['ets_theoretical_optimal'] = result['theoretical_optimal']
        features['ets_tick_efficiency'] = result['tick_efficiency']
        
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

