"""425 - Order Book Slope"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_OrderBookSlope:
    """Order Book Slope - Depth profile slope estimation"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "OrderBookSlope", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Estimate order book slope from price-volume relationship
        # Steep slope = shallow book = low liquidity
        # Flat slope = deep book = high liquidity
        
        # Price levels
        price_range = data['high'] - data['low']
        
        # Volume at different price levels (estimated)
        # Volume near close = executed volume
        volume_concentration = data['volume'] / (price_range + 1e-10)
        
        # Slope estimation
        slope = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Price changes and volume
            price_changes = price_range.iloc[i-period:i].values
            volumes = data['volume'].iloc[i-period:i].values
            
            # Fit line: volume = slope * price_change
            if len(price_changes) > 1 and price_changes.std() > 0:
                slope_val = np.polyfit(price_changes, volumes, 1)[0]
                slope.iloc[i] = slope_val
        
        # Normalize
        slope_normalized = slope / (slope.rolling(50).max() + 1e-10)
        
        # Liquidity score (high slope = high liquidity)
        liquidity = slope_normalized
        liquidity = liquidity.clip(0, 1)
        
        # Slope stability
        slope_stability = 1 / (slope.rolling(period).std() + 1e-10)
        stability_normalized = slope_stability / slope_stability.rolling(50).max()
        
        # Combined score
        combined_score = (liquidity + stability_normalized) / 2
        
        # Smooth
        score_smooth = combined_score.rolling(5).mean()
        
        return pd.DataFrame({
            'price_range': price_range,
            'volume_concentration': volume_concentration,
            'slope': slope,
            'slope_normalized': slope_normalized,
            'liquidity': liquidity,
            'slope_stability': stability_normalized,
            'combined_score': combined_score,
            'score_smooth': score_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High liquidity
        entries = result['score_smooth'] > 0.6
        
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
            'signal_strength': result['score_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Liquid
        entries = result['combined_score'] > 0.6
        
        # Exit: Illiquid
        exits = result['combined_score'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('shallow_book', index=data.index),
            'signal_strength': result['score_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ob_slope_price_range'] = result['price_range']
        features['ob_slope_volume_concentration'] = result['volume_concentration']
        features['ob_slope_value'] = result['slope']
        features['ob_slope_normalized'] = result['slope_normalized']
        features['ob_slope_liquidity'] = result['liquidity']
        features['ob_slope_stability'] = result['slope_stability']
        features['ob_slope_combined_score'] = result['combined_score']
        features['ob_slope_score_smooth'] = result['score_smooth']
        features['ob_slope_high_liquidity'] = (result['combined_score'] > 0.6).astype(int)
        
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

