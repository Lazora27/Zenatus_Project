"""443 - Spoofing Detection (Layering)"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SpoofingDetection:
    """Spoofing Detection - Identifies fake orders (layering/spoofing)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SpoofingDetection", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Spoofing signatures
        
        # 1. Large orders that don't execute (fake liquidity)
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        
        # Price movement without volume (orders pulled)
        price_change = abs(data['close'] - data['close'].shift(1))
        price_change_pct = price_change / data['close'].shift(1)
        
        # Spoofing score: Price moves but volume doesn't follow
        volume_ratio = volume / (avg_volume + 1e-10)
        spoof_score = price_change_pct / (volume_ratio + 1e-10)
        spoof_score_normalized = spoof_score / spoof_score.rolling(50).max()
        
        # 2. Order cancellation proxy (price reversal)
        price_direction = np.sign(data['close'].diff())
        direction_change = (price_direction != price_direction.shift(1)).astype(int)
        cancellation_rate = direction_change.rolling(period).mean()
        
        # 3. Layering detection (repeated patterns)
        price_level = data['close'].round(4)
        level_revisits = price_level.rolling(period).apply(
            lambda x: len(x[x == x.iloc[-1]]) if len(x) > 0 else 0, 
            raw=False
        )
        layering_score = level_revisits / period
        
        # 4. Order book imbalance proxy
        bid_proxy = data['low']
        ask_proxy = data['high']
        imbalance = (ask_proxy - bid_proxy) / data['close']
        imbalance_volatility = imbalance.rolling(period).std()
        
        # High imbalance volatility = spoofing
        spoof_imbalance = imbalance_volatility / imbalance_volatility.rolling(50).max()
        
        # 5. Combined spoofing score
        spoofing_score = (
            spoof_score_normalized * 0.3 +
            cancellation_rate * 0.3 +
            layering_score * 0.2 +
            spoof_imbalance * 0.2
        )
        spoofing_score_smooth = spoofing_score.rolling(5).mean()
        
        # 6. High spoofing periods
        high_spoofing = spoofing_score_smooth > 0.6
        
        # 7. Market integrity score (low spoofing = high integrity)
        integrity_score = 1 - spoofing_score_smooth
        integrity_score_smooth = integrity_score.rolling(5).mean()
        
        # 8. Spoofing intensity
        spoofing_intensity = spoofing_score * cancellation_rate
        spoofing_intensity_smooth = spoofing_intensity.rolling(5).mean()
        
        # 9. Safe trading window
        safe_window = (spoofing_score_smooth < 0.4) & (integrity_score_smooth > 0.6)
        
        # 10. Spoofing trend
        spoofing_trend = spoofing_score_smooth.diff()
        spoofing_acceleration = spoofing_trend.diff()
        
        return pd.DataFrame({
            'volume_ratio': volume_ratio,
            'price_change_pct': price_change_pct,
            'spoof_score': spoof_score_normalized,
            'direction_change': direction_change,
            'cancellation_rate': cancellation_rate,
            'level_revisits': level_revisits,
            'layering_score': layering_score,
            'imbalance': imbalance,
            'imbalance_volatility': imbalance_volatility,
            'spoof_imbalance': spoof_imbalance,
            'spoofing_score': spoofing_score,
            'spoofing_score_smooth': spoofing_score_smooth,
            'high_spoofing': high_spoofing.astype(int),
            'integrity_score': integrity_score,
            'integrity_score_smooth': integrity_score_smooth,
            'spoofing_intensity': spoofing_intensity,
            'spoofing_intensity_smooth': spoofing_intensity_smooth,
            'safe_window': safe_window.astype(int),
            'spoofing_trend': spoofing_trend,
            'spoofing_acceleration': spoofing_acceleration
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe window (no spoofing)
        entries = (result['safe_window'] == 1) & (result['integrity_score_smooth'] > 0.7)
        
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
            'signal_strength': result['integrity_score_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe window
        entries = result['safe_window'] == 1
        
        # Exit: Spoofing detected
        exits = result['high_spoofing'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('spoofing_detected', index=data.index),
            'signal_strength': result['integrity_score_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['spoof_volume_ratio'] = result['volume_ratio']
        features['spoof_price_change_pct'] = result['price_change_pct']
        features['spoof_score'] = result['spoof_score']
        features['spoof_direction_change'] = result['direction_change']
        features['spoof_cancellation_rate'] = result['cancellation_rate']
        features['spoof_level_revisits'] = result['level_revisits']
        features['spoof_layering_score'] = result['layering_score']
        features['spoof_imbalance'] = result['imbalance']
        features['spoof_imbalance_volatility'] = result['imbalance_volatility']
        features['spoof_imbalance_score'] = result['spoof_imbalance']
        features['spoofing_score'] = result['spoofing_score']
        features['spoofing_score_smooth'] = result['spoofing_score_smooth']
        features['spoof_high_spoofing'] = result['high_spoofing']
        features['spoof_integrity_score'] = result['integrity_score']
        features['spoof_integrity_score_smooth'] = result['integrity_score_smooth']
        features['spoof_intensity'] = result['spoofing_intensity']
        features['spoof_intensity_smooth'] = result['spoofing_intensity_smooth']
        features['spoof_safe_window'] = result['safe_window']
        features['spoof_trend'] = result['spoofing_trend']
        features['spoof_acceleration'] = result['spoofing_acceleration']
        
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

