"""454 - Realized Volatility Signature Plot"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RealizedVolatilitySignature:
    """Realized Volatility Signature - Analyzes volatility across time scales"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RealizedVolatilitySignature", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Realized volatility at multiple time scales
        
        # 1. High-frequency volatility (1-bar)
        returns = data['close'].pct_change()
        rv_1bar = returns.rolling(period).std()
        
        # 2. Medium-frequency volatility (5-bar)
        returns_5bar = data['close'].pct_change(5)
        rv_5bar = returns_5bar.rolling(period).std()
        
        # 3. Low-frequency volatility (20-bar)
        returns_20bar = data['close'].pct_change(20)
        rv_20bar = returns_20bar.rolling(period).std()
        
        # 4. Volatility signature slope
        # Downward slope = microstructure noise
        # Flat = efficient market
        slope_5_1 = (rv_5bar - rv_1bar) / 4  # Per bar
        slope_20_5 = (rv_20bar - rv_5bar) / 15
        
        # 5. Microstructure noise indicator
        # Negative slope at short horizons = noise
        noise_indicator = -slope_5_1.clip(upper=0)
        noise_indicator_normalized = noise_indicator / noise_indicator.rolling(50).max()
        
        # 6. Market efficiency score
        # Flat signature = efficient
        signature_flatness = 1 - abs(slope_5_1) / (abs(slope_5_1).rolling(50).max() + 1e-10)
        efficiency_score = signature_flatness
        efficiency_score_smooth = efficiency_score.rolling(5).mean()
        
        # 7. Optimal sampling frequency
        # Where volatility stabilizes
        vol_ratio_5_1 = rv_5bar / (rv_1bar + 1e-10)
        vol_ratio_20_5 = rv_20bar / (rv_5bar + 1e-10)
        
        # Stable ratio = optimal frequency
        sampling_stability = 1 - abs(vol_ratio_5_1 - 1)
        
        # 8. Volatility regime
        avg_rv = rv_1bar.rolling(50).mean()
        high_vol_regime = rv_1bar > avg_rv * 1.5
        low_vol_regime = rv_1bar < avg_rv * 0.5
        normal_vol_regime = ~(high_vol_regime | low_vol_regime)
        
        # 9. Trading quality based on signature
        # Good: Low noise, efficient market, stable volatility
        trading_quality = (
            (1 - noise_indicator_normalized) * 0.4 +
            efficiency_score_smooth * 0.3 +
            sampling_stability * 0.3
        )
        trading_quality_smooth = trading_quality.rolling(5).mean()
        
        # 10. Optimal trading conditions
        optimal_conditions = (
            (trading_quality_smooth > 0.6) &
            (noise_indicator_normalized < 0.4) &
            (normal_vol_regime)
        )
        
        # 11. Volatility signature shape
        # Convex = noise dominated
        # Concave = long memory
        curvature = slope_20_5 - slope_5_1
        convex_signature = curvature < 0
        concave_signature = curvature > 0
        
        return pd.DataFrame({
            'rv_1bar': rv_1bar,
            'rv_5bar': rv_5bar,
            'rv_20bar': rv_20bar,
            'slope_5_1': slope_5_1,
            'slope_20_5': slope_20_5,
            'noise_indicator': noise_indicator_normalized,
            'signature_flatness': signature_flatness,
            'efficiency_score': efficiency_score,
            'efficiency_score_smooth': efficiency_score_smooth,
            'vol_ratio_5_1': vol_ratio_5_1,
            'vol_ratio_20_5': vol_ratio_20_5,
            'sampling_stability': sampling_stability,
            'high_vol_regime': high_vol_regime.astype(int),
            'low_vol_regime': low_vol_regime.astype(int),
            'normal_vol_regime': normal_vol_regime.astype(int),
            'trading_quality': trading_quality,
            'trading_quality_smooth': trading_quality_smooth,
            'optimal_conditions': optimal_conditions.astype(int),
            'curvature': curvature,
            'convex_signature': convex_signature.astype(int),
            'concave_signature': concave_signature.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions
        entries = (result['optimal_conditions'] == 1) & (result['trading_quality_smooth'] > 0.7)
        
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
            'signal_strength': result['trading_quality_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions
        entries = result['optimal_conditions'] == 1
        
        # Exit: Poor trading quality
        exits = result['trading_quality'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('poor_volatility_signature', index=data.index),
            'signal_strength': result['trading_quality_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['rvs_rv_1bar'] = result['rv_1bar']
        features['rvs_rv_5bar'] = result['rv_5bar']
        features['rvs_rv_20bar'] = result['rv_20bar']
        features['rvs_slope_5_1'] = result['slope_5_1']
        features['rvs_slope_20_5'] = result['slope_20_5']
        features['rvs_noise_indicator'] = result['noise_indicator']
        features['rvs_signature_flatness'] = result['signature_flatness']
        features['rvs_efficiency_score'] = result['efficiency_score']
        features['rvs_efficiency_score_smooth'] = result['efficiency_score_smooth']
        features['rvs_vol_ratio_5_1'] = result['vol_ratio_5_1']
        features['rvs_vol_ratio_20_5'] = result['vol_ratio_20_5']
        features['rvs_sampling_stability'] = result['sampling_stability']
        features['rvs_high_vol_regime'] = result['high_vol_regime']
        features['rvs_low_vol_regime'] = result['low_vol_regime']
        features['rvs_normal_vol_regime'] = result['normal_vol_regime']
        features['rvs_trading_quality'] = result['trading_quality']
        features['rvs_trading_quality_smooth'] = result['trading_quality_smooth']
        features['rvs_optimal_conditions'] = result['optimal_conditions']
        features['rvs_curvature'] = result['curvature']
        features['rvs_convex_signature'] = result['convex_signature']
        features['rvs_concave_signature'] = result['concave_signature']
        
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

