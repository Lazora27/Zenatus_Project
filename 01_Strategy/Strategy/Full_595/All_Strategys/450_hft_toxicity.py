"""450 - HFT Toxicity Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HFTToxicity:
    """HFT Toxicity - Measures adverse selection and toxic order flow"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HFTToxicity", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # HFT toxicity measures
        
        # 1. Adverse selection (price moves against you after trade)
        price_change = data['close'].diff()
        future_price_change = price_change.shift(-1)
        
        # Adverse selection score
        adverse_selection = -price_change * future_price_change
        adverse_selection_rate = (adverse_selection > 0).astype(int).rolling(period).mean()
        
        # 2. Toxic order flow (informed trading)
        volume = data['volume']
        price_impact = abs(price_change) / data['close']
        
        # High impact per unit volume = toxic flow
        toxicity = price_impact * volume
        toxicity_normalized = toxicity / toxicity.rolling(50).max()
        
        # 3. Information asymmetry
        # Fast price discovery = informed traders
        price_velocity = abs(price_change) / (data.index.to_series().diff().dt.total_seconds() + 1e-10)
        price_velocity.index = data.index
        
        info_asymmetry = price_velocity * volume
        info_asymmetry_normalized = info_asymmetry / info_asymmetry.rolling(50).max()
        
        # 4. Market maker adverse selection cost
        spread_proxy = data['high'] - data['low']
        realized_spread = spread_proxy - abs(future_price_change)
        
        # Negative realized spread = adverse selection
        adverse_cost = -realized_spread / (spread_proxy + 1e-10)
        adverse_cost_normalized = adverse_cost / adverse_cost.rolling(50).max()
        
        # 5. Combined toxicity score
        toxicity_score = (
            adverse_selection_rate * 0.3 +
            toxicity_normalized * 0.3 +
            info_asymmetry_normalized * 0.2 +
            adverse_cost_normalized * 0.2
        )
        toxicity_score_smooth = toxicity_score.rolling(5).mean()
        
        # 6. High toxicity periods
        high_toxicity = toxicity_score_smooth > 0.6
        
        # 7. Market health (low toxicity)
        market_health = 1 - toxicity_score_smooth
        market_health_smooth = market_health.rolling(5).mean()
        
        # 8. Safe trading conditions
        safe_conditions = (toxicity_score_smooth < 0.4) & (market_health_smooth > 0.6)
        
        # 9. Toxicity intensity
        toxicity_intensity = toxicity_score * volume / volume.rolling(period).mean()
        toxicity_intensity_smooth = toxicity_intensity.rolling(5).mean()
        
        # 10. Informed trader presence
        informed_trading = (
            (adverse_selection_rate > 0.6) &
            (info_asymmetry_normalized > 0.7)
        )
        
        # 11. Market maker stress
        mm_stress = adverse_cost_normalized * toxicity_score_smooth
        mm_stress_smooth = mm_stress.rolling(5).mean()
        
        # 12. Toxicity trend
        toxicity_trend = toxicity_score_smooth.diff()
        toxicity_acceleration = toxicity_trend.diff()
        
        return pd.DataFrame({
            'adverse_selection': adverse_selection,
            'adverse_selection_rate': adverse_selection_rate,
            'price_impact': price_impact,
            'toxicity': toxicity_normalized,
            'price_velocity': price_velocity,
            'info_asymmetry': info_asymmetry_normalized,
            'spread_proxy': spread_proxy,
            'realized_spread': realized_spread,
            'adverse_cost': adverse_cost_normalized,
            'toxicity_score': toxicity_score,
            'toxicity_score_smooth': toxicity_score_smooth,
            'high_toxicity': high_toxicity.astype(int),
            'market_health': market_health,
            'market_health_smooth': market_health_smooth,
            'safe_conditions': safe_conditions.astype(int),
            'toxicity_intensity': toxicity_intensity,
            'toxicity_intensity_smooth': toxicity_intensity_smooth,
            'informed_trading': informed_trading.astype(int),
            'mm_stress': mm_stress,
            'mm_stress_smooth': mm_stress_smooth,
            'toxicity_trend': toxicity_trend,
            'toxicity_acceleration': toxicity_acceleration
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions (low toxicity)
        entries = (result['safe_conditions'] == 1) & (result['market_health_smooth'] > 0.7)
        
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
            'signal_strength': result['market_health_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions
        entries = result['safe_conditions'] == 1
        
        # Exit: High toxicity
        exits = result['high_toxicity'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_toxicity_detected', index=data.index),
            'signal_strength': result['market_health_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['hft_adverse_selection'] = result['adverse_selection']
        features['hft_adverse_selection_rate'] = result['adverse_selection_rate']
        features['hft_price_impact'] = result['price_impact']
        features['hft_toxicity'] = result['toxicity']
        features['hft_price_velocity'] = result['price_velocity']
        features['hft_info_asymmetry'] = result['info_asymmetry']
        features['hft_spread_proxy'] = result['spread_proxy']
        features['hft_realized_spread'] = result['realized_spread']
        features['hft_adverse_cost'] = result['adverse_cost']
        features['hft_toxicity_score'] = result['toxicity_score']
        features['hft_toxicity_score_smooth'] = result['toxicity_score_smooth']
        features['hft_high_toxicity'] = result['high_toxicity']
        features['hft_market_health'] = result['market_health']
        features['hft_market_health_smooth'] = result['market_health_smooth']
        features['hft_safe_conditions'] = result['safe_conditions']
        features['hft_toxicity_intensity'] = result['toxicity_intensity']
        features['hft_toxicity_intensity_smooth'] = result['toxicity_intensity_smooth']
        features['hft_informed_trading'] = result['informed_trading']
        features['hft_mm_stress'] = result['mm_stress']
        features['hft_mm_stress_smooth'] = result['mm_stress_smooth']
        features['hft_toxicity_trend'] = result['toxicity_trend']
        features['hft_toxicity_acceleration'] = result['toxicity_acceleration']
        
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

