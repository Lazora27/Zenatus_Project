"""448 - Liquidity Hunting Detection"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_LiquidityHunting:
    """Liquidity Hunting - Detects stop-loss hunting and liquidity raids"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "LiquidityHunting", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Liquidity hunting signatures
        
        # 1. Stop-loss levels (support/resistance)
        support = data['low'].rolling(period).min()
        resistance = data['high'].rolling(period).max()
        
        # 2. Liquidity raid detection (price spikes through levels)
        support_breach = data['low'] < support.shift(1)
        resistance_breach = data['high'] > resistance.shift(1)
        
        # 3. Quick reversal after breach (hunt signature)
        price_after_breach = data['close']
        support_hunt = support_breach & (price_after_breach > support.shift(1))
        resistance_hunt = resistance_breach & (price_after_breach < resistance.shift(1))
        
        # 4. Hunt frequency
        hunt_events = support_hunt | resistance_hunt
        hunt_frequency = hunt_events.astype(int).rolling(period).sum()
        
        # 5. Volume during hunt
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_spike = volume / (avg_volume + 1e-10)
        
        hunt_volume = volume_spike * hunt_events.astype(int)
        
        # 6. Liquidity hunting score
        hunt_score = hunt_frequency * hunt_volume
        hunt_score_normalized = hunt_score / hunt_score.rolling(50).max()
        hunt_score_smooth = hunt_score_normalized.rolling(5).mean()
        
        # 7. High hunting periods
        high_hunting = hunt_score_smooth > 0.6
        
        # 8. Wick analysis (long wicks = liquidity raids)
        upper_wick = data['high'] - np.maximum(data['open'], data['close'])
        lower_wick = np.minimum(data['open'], data['close']) - data['low']
        body = abs(data['close'] - data['open'])
        
        upper_wick_ratio = upper_wick / (body + 1e-10)
        lower_wick_ratio = lower_wick / (body + 1e-10)
        
        # Long wicks = liquidity hunt
        wick_hunt = (upper_wick_ratio > 2) | (lower_wick_ratio > 2)
        
        # 9. Market safety score
        safety_score = 1 - hunt_score_smooth
        safety_score_smooth = safety_score.rolling(5).mean()
        
        # 10. Safe trading conditions
        safe_conditions = (hunt_score_smooth < 0.4) & (safety_score_smooth > 0.6)
        
        # 11. Hunt direction
        hunt_direction = np.where(support_hunt, -1, np.where(resistance_hunt, 1, 0))
        
        # 12. Distance to key levels
        distance_to_support = (data['close'] - support) / data['close']
        distance_to_resistance = (resistance - data['close']) / data['close']
        
        # Close to levels = high risk
        near_levels = (distance_to_support < 0.01) | (distance_to_resistance < 0.01)
        
        return pd.DataFrame({
            'support': support,
            'resistance': resistance,
            'support_breach': support_breach.astype(int),
            'resistance_breach': resistance_breach.astype(int),
            'support_hunt': support_hunt.astype(int),
            'resistance_hunt': resistance_hunt.astype(int),
            'hunt_events': hunt_events.astype(int),
            'hunt_frequency': hunt_frequency,
            'volume_spike': volume_spike,
            'hunt_volume': hunt_volume,
            'hunt_score': hunt_score_normalized,
            'hunt_score_smooth': hunt_score_smooth,
            'high_hunting': high_hunting.astype(int),
            'upper_wick_ratio': upper_wick_ratio,
            'lower_wick_ratio': lower_wick_ratio,
            'wick_hunt': wick_hunt.astype(int),
            'safety_score': safety_score,
            'safety_score_smooth': safety_score_smooth,
            'safe_conditions': safe_conditions.astype(int),
            'hunt_direction': hunt_direction,
            'distance_to_support': distance_to_support,
            'distance_to_resistance': distance_to_resistance,
            'near_levels': near_levels.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions (low hunting activity)
        entries = (result['safe_conditions'] == 1) & (result['safety_score_smooth'] > 0.7)
        
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
            'signal_strength': result['safety_score_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions
        entries = result['safe_conditions'] == 1
        
        # Exit: High hunting activity
        exits = result['high_hunting'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('liquidity_hunting_detected', index=data.index),
            'signal_strength': result['safety_score_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['lh_support'] = result['support']
        features['lh_resistance'] = result['resistance']
        features['lh_support_breach'] = result['support_breach']
        features['lh_resistance_breach'] = result['resistance_breach']
        features['lh_support_hunt'] = result['support_hunt']
        features['lh_resistance_hunt'] = result['resistance_hunt']
        features['lh_hunt_events'] = result['hunt_events']
        features['lh_hunt_frequency'] = result['hunt_frequency']
        features['lh_volume_spike'] = result['volume_spike']
        features['lh_hunt_volume'] = result['hunt_volume']
        features['lh_hunt_score'] = result['hunt_score']
        features['lh_hunt_score_smooth'] = result['hunt_score_smooth']
        features['lh_high_hunting'] = result['high_hunting']
        features['lh_upper_wick_ratio'] = result['upper_wick_ratio']
        features['lh_lower_wick_ratio'] = result['lower_wick_ratio']
        features['lh_wick_hunt'] = result['wick_hunt']
        features['lh_safety_score'] = result['safety_score']
        features['lh_safety_score_smooth'] = result['safety_score_smooth']
        features['lh_safe_conditions'] = result['safe_conditions']
        features['lh_hunt_direction'] = result['hunt_direction']
        features['lh_distance_to_support'] = result['distance_to_support']
        features['lh_distance_to_resistance'] = result['distance_to_resistance']
        features['lh_near_levels'] = result['near_levels']
        
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

