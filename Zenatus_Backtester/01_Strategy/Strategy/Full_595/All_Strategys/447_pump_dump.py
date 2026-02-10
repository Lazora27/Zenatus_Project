"""447 - Pump and Dump Detection"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PumpDump:
    """Pump and Dump - Detects coordinated price manipulation schemes"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PumpDump", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Pump and dump signatures
        
        # 1. Pump phase: Rapid price increase + volume spike
        price_change = data['close'].pct_change()
        price_increase = price_change.rolling(5).sum()
        
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_ratio = volume / (avg_volume + 1e-10)
        
        # Pump score
        pump_score = price_increase * volume_ratio
        pump_score_normalized = pump_score / pump_score.rolling(50).max()
        
        # 2. Dump phase: Rapid price decrease
        price_decrease = -price_change.rolling(5).sum()
        dump_score = price_decrease * volume_ratio
        dump_score_normalized = dump_score / dump_score.rolling(50).max()
        
        # 3. Pump detection
        pump_threshold = pump_score_normalized.rolling(50).quantile(0.9)
        pump_detected = pump_score_normalized > pump_threshold
        
        # 4. Dump detection (follows pump)
        dump_threshold = dump_score_normalized.rolling(50).quantile(0.9)
        dump_detected = dump_score_normalized > dump_threshold
        
        # 5. Pump-dump cycle
        pump_dump_cycle = pump_detected.shift(5).rolling(10).max().astype(bool) & dump_detected.astype(bool)
        
        # 6. Price volatility spike
        volatility = data['close'].rolling(period).std()
        avg_volatility = volatility.rolling(50).mean()
        volatility_spike = volatility / (avg_volatility + 1e-10)
        
        # 7. Pump-dump score
        pd_score = (
            pump_score_normalized * 0.3 +
            dump_score_normalized * 0.3 +
            pump_dump_cycle.astype(int) * 0.2 +
            volatility_spike * 0.2
        )
        pd_score_smooth = pd_score.rolling(5).mean()
        
        # 8. High risk periods
        high_risk = pd_score_smooth > 0.6
        
        # 9. Market stability score
        stability = 1 - pd_score_smooth
        stability_smooth = stability.rolling(5).mean()
        
        # 10. Safe trading window
        safe_window = (pd_score_smooth < 0.4).astype(bool) & (stability_smooth > 0.6).astype(bool)
        
        # 11. Pump phase indicator
        in_pump_phase = pump_detected.astype(bool) & ~dump_detected.astype(bool)
        
        # 12. Dump phase indicator
        in_dump_phase = dump_detected.astype(bool) & pump_detected.shift(5).rolling(10).max().astype(bool)
        
        # 13. Recovery phase (after dump)
        recovery_phase = dump_detected.shift(5).astype(bool) & ~pump_detected.astype(bool) & ~dump_detected.astype(bool)
        
        return pd.DataFrame({
            'price_increase': price_increase,
            'volume_ratio': volume_ratio,
            'pump_score': pump_score_normalized,
            'price_decrease': price_decrease,
            'dump_score': dump_score_normalized,
            'pump_detected': pump_detected.astype(int),
            'dump_detected': dump_detected.astype(int),
            'pump_dump_cycle': pump_dump_cycle.astype(int),
            'volatility': volatility,
            'volatility_spike': volatility_spike,
            'pd_score': pd_score,
            'pd_score_smooth': pd_score_smooth,
            'high_risk': high_risk.astype(int),
            'stability': stability,
            'stability_smooth': stability_smooth,
            'safe_window': safe_window.astype(int),
            'in_pump_phase': in_pump_phase.astype(int),
            'in_dump_phase': in_dump_phase.astype(int),
            'recovery_phase': recovery_phase.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe window (stable market)
        entries = (result['safe_window'] == 1) & (result['stability_smooth'] > 0.7)
        
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
            'signal_strength': result['stability_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe window
        entries = result['safe_window'] == 1
        
        # Exit: High risk (pump or dump detected)
        exits = result['high_risk'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pump_dump_detected', index=data.index),
            'signal_strength': result['stability_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['pd_price_increase'] = result['price_increase']
        features['pd_volume_ratio'] = result['volume_ratio']
        features['pd_pump_score'] = result['pump_score']
        features['pd_price_decrease'] = result['price_decrease']
        features['pd_dump_score'] = result['dump_score']
        features['pd_pump_detected'] = result['pump_detected']
        features['pd_dump_detected'] = result['dump_detected']
        features['pd_pump_dump_cycle'] = result['pump_dump_cycle']
        features['pd_volatility'] = result['volatility']
        features['pd_volatility_spike'] = result['volatility_spike']
        features['pd_score'] = result['pd_score']
        features['pd_score_smooth'] = result['pd_score_smooth']
        features['pd_high_risk'] = result['high_risk']
        features['pd_stability'] = result['stability']
        features['pd_stability_smooth'] = result['stability_smooth']
        features['pd_safe_window'] = result['safe_window']
        features['pd_in_pump_phase'] = result['in_pump_phase']
        features['pd_in_dump_phase'] = result['in_dump_phase']
        features['pd_recovery_phase'] = result['recovery_phase']
        
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

