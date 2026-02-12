"""445 - Front Running Detection"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FrontRunning:
    """Front Running - Detects front-running activity (predatory trading)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FrontRunning", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Front running signatures
        
        # 1. Price anticipation (price moves before large orders)
        price_change = data['close'].diff()
        volume = data['volume']
        
        # Lead-lag relationship
        price_lead = price_change
        volume_lag = volume.shift(-1)  # Volume follows price
        
        # Front running score: Price moves, then volume follows
        avg_volume = volume.rolling(period).mean()
        volume_spike_lag = volume_lag / (avg_volume + 1e-10)
        
        price_momentum = abs(price_change) / data['close']
        front_run_score = price_momentum * volume_spike_lag
        front_run_score_normalized = front_run_score / front_run_score.rolling(50).max()
        
        # 2. Predictive price movement
        price_acceleration = price_change.diff()
        volume_acceleration = volume.diff()
        
        # Price accelerates before volume
        predictive_pattern = (abs(price_acceleration) > price_acceleration.rolling(period).std()) & \
                            (volume_acceleration.shift(-1) > volume_acceleration.rolling(period).std())
        
        # 3. Order flow anticipation
        price_direction = np.sign(price_change)
        volume_direction = np.sign(volume.diff())
        
        # Price direction predicts volume direction
        direction_match = (price_direction == volume_direction.shift(-1)).astype(int)
        anticipation_rate = direction_match.rolling(period).mean()
        
        # 4. Slippage proxy (victims pay more)
        intrabar_range = data['high'] - data['low']
        slippage_proxy = intrabar_range / data['close']
        avg_slippage = slippage_proxy.rolling(period).mean()
        
        # High slippage = front running activity
        slippage_excess = slippage_proxy / (avg_slippage + 1e-10)
        slippage_excess_normalized = slippage_excess / slippage_excess.rolling(50).max()
        
        # 5. Combined front running score
        front_running_score = (
            front_run_score_normalized * 0.3 +
            predictive_pattern.astype(int) * 0.3 +
            anticipation_rate * 0.2 +
            slippage_excess_normalized * 0.2
        )
        front_running_score_smooth = front_running_score.rolling(5).mean()
        
        # 6. High front running periods
        high_front_running = front_running_score_smooth > 0.6
        
        # 7. Market fairness score (low front running)
        fairness_score = 1 - front_running_score_smooth
        fairness_score_smooth = fairness_score.rolling(5).mean()
        
        # 8. Front running intensity
        front_run_intensity = front_running_score * volume_spike_lag
        front_run_intensity_smooth = front_run_intensity.rolling(5).mean()
        
        # 9. Safe trading conditions
        safe_conditions = (front_running_score_smooth < 0.4) & (fairness_score_smooth > 0.6)
        
        # 10. Victim detection (high slippage + volume spike)
        victim_pattern = (slippage_excess_normalized > 0.7) & (volume_spike_lag > 1.5)
        
        # 11. Front running trend
        front_run_trend = front_running_score_smooth.diff()
        front_run_acceleration = front_run_trend.diff()
        
        return pd.DataFrame({
            'price_momentum': price_momentum,
            'volume_spike_lag': volume_spike_lag,
            'front_run_score': front_run_score_normalized,
            'price_acceleration': price_acceleration,
            'volume_acceleration': volume_acceleration,
            'predictive_pattern': predictive_pattern.astype(int),
            'direction_match': direction_match,
            'anticipation_rate': anticipation_rate,
            'slippage_proxy': slippage_proxy,
            'slippage_excess': slippage_excess_normalized,
            'front_running_score': front_running_score,
            'front_running_score_smooth': front_running_score_smooth,
            'high_front_running': high_front_running.astype(int),
            'fairness_score': fairness_score,
            'fairness_score_smooth': fairness_score_smooth,
            'front_run_intensity': front_run_intensity,
            'front_run_intensity_smooth': front_run_intensity_smooth,
            'safe_conditions': safe_conditions.astype(int),
            'victim_pattern': victim_pattern.astype(int),
            'front_run_trend': front_run_trend,
            'front_run_acceleration': front_run_acceleration
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions (no front running)
        entries = (result['safe_conditions'] == 1) & (result['fairness_score_smooth'] > 0.7)
        
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
            'signal_strength': result['fairness_score_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions
        entries = result['safe_conditions'] == 1
        
        # Exit: Front running detected
        exits = result['high_front_running'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('front_running_detected', index=data.index),
            'signal_strength': result['fairness_score_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['fr_price_momentum'] = result['price_momentum']
        features['fr_volume_spike_lag'] = result['volume_spike_lag']
        features['fr_score'] = result['front_run_score']
        features['fr_price_acceleration'] = result['price_acceleration']
        features['fr_volume_acceleration'] = result['volume_acceleration']
        features['fr_predictive_pattern'] = result['predictive_pattern']
        features['fr_direction_match'] = result['direction_match']
        features['fr_anticipation_rate'] = result['anticipation_rate']
        features['fr_slippage_proxy'] = result['slippage_proxy']
        features['fr_slippage_excess'] = result['slippage_excess']
        features['front_running_score'] = result['front_running_score']
        features['front_running_score_smooth'] = result['front_running_score_smooth']
        features['fr_high_front_running'] = result['high_front_running']
        features['fr_fairness_score'] = result['fairness_score']
        features['fr_fairness_score_smooth'] = result['fairness_score_smooth']
        features['fr_intensity'] = result['front_run_intensity']
        features['fr_intensity_smooth'] = result['front_run_intensity_smooth']
        features['fr_safe_conditions'] = result['safe_conditions']
        features['fr_victim_pattern'] = result['victim_pattern']
        features['fr_trend'] = result['front_run_trend']
        features['fr_acceleration'] = result['front_run_acceleration']
        
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

