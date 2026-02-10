"""446 - Momentum Ignition Detection"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MomentumIgnition:
    """Momentum Ignition - Detects artificial momentum creation (manipulation)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MomentumIgnition", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Momentum ignition signatures
        
        # 1. Sudden price acceleration
        price_change = data['close'].diff()
        price_acceleration = price_change.diff()
        
        # Abnormal acceleration
        avg_acceleration = price_acceleration.rolling(period).mean()
        std_acceleration = price_acceleration.rolling(period).std()
        acceleration_zscore = (price_acceleration - avg_acceleration) / (std_acceleration + 1e-10)
        
        # 2. Volume spike during ignition
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_spike = volume / (avg_volume + 1e-10)
        
        # 3. Ignition score (high acceleration + volume)
        ignition_score = abs(acceleration_zscore) * volume_spike
        ignition_score_normalized = ignition_score / ignition_score.rolling(50).max()
        
        # 4. Momentum sustainability (real vs fake)
        momentum = price_change.rolling(5).sum()
        momentum_decay = momentum.diff()
        
        # Fast decay = fake momentum
        sustainability = abs(momentum) / (abs(momentum_decay) + 1e-10)
        sustainability_normalized = sustainability / sustainability.rolling(50).max()
        
        # 5. Ignition pattern detection
        ignition_pattern = (
            (abs(acceleration_zscore) > 2) &  # Strong acceleration
            (volume_spike > 1.5) &             # Volume spike
            (sustainability_normalized < 0.5)  # Low sustainability
        )
        
        # 6. Ignition intensity
        ignition_intensity = ignition_score_normalized * (1 - sustainability_normalized)
        ignition_intensity_smooth = ignition_intensity.rolling(5).mean()
        
        # 7. High ignition periods
        high_ignition = ignition_intensity_smooth > 0.6
        
        # 8. Natural momentum score
        natural_momentum = sustainability_normalized * (1 - ignition_intensity_smooth)
        natural_momentum_smooth = natural_momentum.rolling(5).mean()
        
        # 9. Safe trading conditions
        safe_conditions = (ignition_intensity_smooth < 0.4) & (natural_momentum_smooth > 0.5)
        
        # 10. Reversal probability (after ignition)
        reversal_signal = high_ignition.shift(1) & (ignition_intensity_smooth < 0.3)
        
        # 11. Price direction during ignition
        ignition_direction = np.sign(price_change) * ignition_pattern.astype(int)
        
        return pd.DataFrame({
            'price_acceleration': price_acceleration,
            'acceleration_zscore': acceleration_zscore,
            'volume_spike': volume_spike,
            'ignition_score': ignition_score_normalized,
            'momentum': momentum,
            'momentum_decay': momentum_decay,
            'sustainability': sustainability_normalized,
            'ignition_pattern': ignition_pattern.astype(int),
            'ignition_intensity': ignition_intensity,
            'ignition_intensity_smooth': ignition_intensity_smooth,
            'high_ignition': high_ignition.astype(int),
            'natural_momentum': natural_momentum,
            'natural_momentum_smooth': natural_momentum_smooth,
            'safe_conditions': safe_conditions.astype(int),
            'reversal_signal': reversal_signal.astype(int),
            'ignition_direction': ignition_direction
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions (natural momentum)
        entries = (result['safe_conditions'] == 1) & (result['natural_momentum_smooth'] > 0.6)
        
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
            'signal_strength': result['natural_momentum_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions
        entries = result['safe_conditions'] == 1
        
        # Exit: Ignition detected
        exits = result['high_ignition'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('momentum_ignition_detected', index=data.index),
            'signal_strength': result['natural_momentum_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['mi_price_acceleration'] = result['price_acceleration']
        features['mi_acceleration_zscore'] = result['acceleration_zscore']
        features['mi_volume_spike'] = result['volume_spike']
        features['mi_ignition_score'] = result['ignition_score']
        features['mi_momentum'] = result['momentum']
        features['mi_momentum_decay'] = result['momentum_decay']
        features['mi_sustainability'] = result['sustainability']
        features['mi_ignition_pattern'] = result['ignition_pattern']
        features['mi_ignition_intensity'] = result['ignition_intensity']
        features['mi_ignition_intensity_smooth'] = result['ignition_intensity_smooth']
        features['mi_high_ignition'] = result['high_ignition']
        features['mi_natural_momentum'] = result['natural_momentum']
        features['mi_natural_momentum_smooth'] = result['natural_momentum_smooth']
        features['mi_safe_conditions'] = result['safe_conditions']
        features['mi_reversal_signal'] = result['reversal_signal']
        features['mi_ignition_direction'] = result['ignition_direction']
        
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

