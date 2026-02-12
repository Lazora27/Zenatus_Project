"""455 - Price Discovery Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PriceDiscovery:
    """Price Discovery - Measures information incorporation efficiency"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PriceDiscovery", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Price discovery metrics
        
        # 1. Information share (Hasbrouck)
        # Variance of permanent price component
        returns = data['close'].pct_change()
        
        # Permanent component (random walk)
        permanent = returns.rolling(period).sum()
        permanent_var = permanent.rolling(period).var()
        
        # Total variance
        total_var = returns.rolling(period).var() * period
        
        # Information share
        info_share = permanent_var / (total_var + 1e-10)
        info_share = info_share.clip(0, 1)
        
        # 2. Price discovery speed
        # How fast does price incorporate information?
        price_change = data['close'].diff()
        abs_price_change = abs(price_change)
        
        # Cumulative price change
        cumulative_change = abs_price_change.rolling(5).sum()
        
        # Discovery speed = change per unit time
        discovery_speed = cumulative_change / 5
        discovery_speed_normalized = discovery_speed / discovery_speed.rolling(50).max()
        
        # 3. Price efficiency ratio
        # Actual path vs direct path
        direct_path = abs(data['close'] - data['close'].shift(period))
        actual_path = abs_price_change.rolling(period).sum()
        
        efficiency_ratio = direct_path / (actual_path + 1e-10)
        efficiency_ratio = efficiency_ratio.clip(0, 1)
        
        # 4. Information arrival rate
        # Frequency of significant price changes
        significant_change = (abs_price_change > abs_price_change.rolling(period).std()).astype(int)
        info_arrival_rate = significant_change.rolling(period).mean()
        
        # 5. Price discovery quality
        # High info share + high efficiency = good discovery
        discovery_quality = (
            info_share * 0.4 +
            efficiency_ratio * 0.3 +
            info_arrival_rate * 0.3
        )
        discovery_quality_smooth = discovery_quality.rolling(5).mean()
        
        # 6. Informed trading indicator
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_spike = volume / (avg_volume + 1e-10)
        
        # Informed trading = volume spike + significant price change
        informed_trading = volume_spike * significant_change
        informed_trading_rate = informed_trading.rolling(period).mean()
        
        # 7. Price discovery regimes
        high_discovery = discovery_quality_smooth > 0.7
        low_discovery = discovery_quality_smooth < 0.3
        normal_discovery = ~(high_discovery | low_discovery)
        
        # 8. Optimal trading conditions
        # Good discovery + informed trading
        optimal_conditions = (
            (discovery_quality_smooth > 0.6) &
            (efficiency_ratio > 0.5) &
            (info_arrival_rate > 0.3)
        )
        
        # 9. Discovery momentum
        discovery_momentum = discovery_quality_smooth.diff()
        discovery_accelerating = discovery_momentum > 0
        
        # 10. Market informativeness
        # How much information is in prices?
        price_informativeness = info_share * info_arrival_rate
        price_informativeness_smooth = price_informativeness.rolling(5).mean()
        
        # 11. Discovery contribution score
        # Contribution to price discovery process
        contribution_score = (
            discovery_speed_normalized * 0.3 +
            info_share * 0.3 +
            informed_trading_rate * 0.4
        )
        contribution_score_smooth = contribution_score.rolling(5).mean()
        
        return pd.DataFrame({
            'permanent': permanent,
            'permanent_var': permanent_var,
            'total_var': total_var,
            'info_share': info_share,
            'cumulative_change': cumulative_change,
            'discovery_speed': discovery_speed_normalized,
            'direct_path': direct_path,
            'actual_path': actual_path,
            'efficiency_ratio': efficiency_ratio,
            'significant_change': significant_change,
            'info_arrival_rate': info_arrival_rate,
            'discovery_quality': discovery_quality,
            'discovery_quality_smooth': discovery_quality_smooth,
            'volume_spike': volume_spike,
            'informed_trading': informed_trading,
            'informed_trading_rate': informed_trading_rate,
            'high_discovery': high_discovery.astype(int),
            'low_discovery': low_discovery.astype(int),
            'normal_discovery': normal_discovery.astype(int),
            'optimal_conditions': optimal_conditions.astype(int),
            'discovery_momentum': discovery_momentum,
            'discovery_accelerating': discovery_accelerating.astype(int),
            'price_informativeness': price_informativeness,
            'price_informativeness_smooth': price_informativeness_smooth,
            'contribution_score': contribution_score,
            'contribution_score_smooth': contribution_score_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions (good price discovery)
        entries = (result['optimal_conditions'] == 1) & (result['discovery_quality_smooth'] > 0.7)
        
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
            'signal_strength': result['discovery_quality_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Optimal conditions
        entries = result['optimal_conditions'] == 1
        
        # Exit: Low discovery
        exits = result['low_discovery'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('low_price_discovery', index=data.index),
            'signal_strength': result['discovery_quality_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['pd_permanent'] = result['permanent']
        features['pd_permanent_var'] = result['permanent_var']
        features['pd_total_var'] = result['total_var']
        features['pd_info_share'] = result['info_share']
        features['pd_cumulative_change'] = result['cumulative_change']
        features['pd_discovery_speed'] = result['discovery_speed']
        features['pd_direct_path'] = result['direct_path']
        features['pd_actual_path'] = result['actual_path']
        features['pd_efficiency_ratio'] = result['efficiency_ratio']
        features['pd_significant_change'] = result['significant_change']
        features['pd_info_arrival_rate'] = result['info_arrival_rate']
        features['pd_discovery_quality'] = result['discovery_quality']
        features['pd_discovery_quality_smooth'] = result['discovery_quality_smooth']
        features['pd_volume_spike'] = result['volume_spike']
        features['pd_informed_trading'] = result['informed_trading']
        features['pd_informed_trading_rate'] = result['informed_trading_rate']
        features['pd_high_discovery'] = result['high_discovery']
        features['pd_low_discovery'] = result['low_discovery']
        features['pd_normal_discovery'] = result['normal_discovery']
        features['pd_optimal_conditions'] = result['optimal_conditions']
        features['pd_discovery_momentum'] = result['discovery_momentum']
        features['pd_discovery_accelerating'] = result['discovery_accelerating']
        features['pd_price_informativeness'] = result['price_informativeness']
        features['pd_price_informativeness_smooth'] = result['price_informativeness_smooth']
        features['pd_contribution_score'] = result['contribution_score']
        features['pd_contribution_score_smooth'] = result['contribution_score_smooth']
        
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

