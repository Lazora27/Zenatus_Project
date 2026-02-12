"""471 - Market Impact Model (Almgren-Chriss)"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MarketImpactModel:
    """Market Impact Model - Predicts price impact of trades (Almgren-Chriss)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MarketImpactModel", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Market impact components (Almgren-Chriss model)
        
        # 1. Temporary impact (immediate price movement)
        price_change = abs(data['close'] - data['open'])
        volume = data['volume']
        
        # Impact per unit volume
        temporary_impact = price_change / (volume + 1e-10)
        temporary_impact_normalized = temporary_impact / temporary_impact.rolling(50).max()
        
        # 2. Permanent impact (lasting price change)
        permanent_change = abs(data['close'] - data['close'].shift(period))
        permanent_impact = permanent_change / (volume.rolling(period).sum() + 1e-10)
        permanent_impact_normalized = permanent_impact / permanent_impact.rolling(50).max()
        
        # 3. Total market impact
        total_impact = temporary_impact_normalized + permanent_impact_normalized
        total_impact_smooth = total_impact.rolling(5).mean()
        
        # 4. Impact decay rate
        # How fast does temporary impact decay?
        impact_decay = (temporary_impact_normalized - permanent_impact_normalized) / (temporary_impact_normalized + 1e-10)
        impact_decay = impact_decay.clip(0, 1)
        
        # 5. Liquidity parameter (Kyle's lambda)
        price_change_signed = data['close'] - data['open']
        signed_volume = volume * np.sign(price_change_signed)
        
        # Lambda = price impact per unit signed volume
        kyle_lambda = abs(price_change_signed) / (abs(signed_volume) + 1e-10)
        kyle_lambda_normalized = kyle_lambda / kyle_lambda.rolling(50).max()
        kyle_lambda_smooth = kyle_lambda_normalized.rolling(5).mean()
        
        # 6. Market depth (inverse of impact)
        market_depth = 1 / (total_impact_smooth + 1e-10)
        market_depth_normalized = market_depth / market_depth.rolling(50).max()
        
        # 7. Impact volatility
        impact_std = total_impact.rolling(period).std()
        impact_volatility = impact_std / (total_impact.rolling(period).mean() + 1e-10)
        
        # 8. Predictable impact
        # Low volatility = predictable
        impact_predictability = 1 / (impact_volatility + 1e-10)
        impact_predictability_normalized = impact_predictability / impact_predictability.rolling(50).max()
        
        # 9. Optimal trading size
        # Based on impact model
        avg_volume = volume.rolling(period).mean()
        optimal_size = avg_volume * (1 - total_impact_smooth)
        optimal_size_normalized = optimal_size / optimal_size.rolling(50).max()
        
        # 10. Impact cost estimate
        # Expected cost for typical trade
        impact_cost = total_impact_smooth * avg_volume / volume
        impact_cost_smooth = impact_cost.rolling(5).mean()
        
        # 11. Low impact periods
        low_impact = total_impact_smooth < total_impact_smooth.rolling(50).quantile(0.25)
        
        # 12. High impact periods
        high_impact = total_impact_smooth > total_impact_smooth.rolling(50).quantile(0.75)
        
        # 13. Optimal execution conditions
        optimal_conditions = (
            (low_impact) &
            (market_depth_normalized > 0.5) &
            (impact_predictability_normalized > 0.5)
        )
        
        # 14. Impact efficiency
        # Actual impact vs expected
        expected_impact = total_impact.rolling(period).mean()
        impact_efficiency = expected_impact / (total_impact + 1e-10)
        impact_efficiency_normalized = impact_efficiency / impact_efficiency.rolling(50).max()
        
        return pd.DataFrame({
            'temporary_impact': temporary_impact_normalized,
            'permanent_impact': permanent_impact_normalized,
            'total_impact': total_impact,
            'total_impact_smooth': total_impact_smooth,
            'impact_decay': impact_decay,
            'kyle_lambda': kyle_lambda_normalized,
            'kyle_lambda_smooth': kyle_lambda_smooth,
            'market_depth': market_depth_normalized,
            'impact_std': impact_std,
            'impact_volatility': impact_volatility,
            'impact_predictability': impact_predictability_normalized,
            'optimal_size': optimal_size_normalized,
            'impact_cost': impact_cost,
            'impact_cost_smooth': impact_cost_smooth,
            'low_impact': low_impact.astype(int),
            'high_impact': high_impact.astype(int),
            'optimal_conditions': optimal_conditions.astype(int),
            'impact_efficiency': impact_efficiency_normalized
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low impact periods
        entries = (result['optimal_conditions'] == 1) & (result['market_depth'] > 0.6)
        
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
            'signal_strength': result['market_depth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low impact
        entries = result['low_impact'] == 1
        
        # Exit: High impact
        exits = result['high_impact'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_market_impact', index=data.index),
            'signal_strength': result['market_depth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['mim_temporary_impact'] = result['temporary_impact']
        features['mim_permanent_impact'] = result['permanent_impact']
        features['mim_total_impact'] = result['total_impact']
        features['mim_total_impact_smooth'] = result['total_impact_smooth']
        features['mim_impact_decay'] = result['impact_decay']
        features['mim_kyle_lambda'] = result['kyle_lambda']
        features['mim_kyle_lambda_smooth'] = result['kyle_lambda_smooth']
        features['mim_market_depth'] = result['market_depth']
        features['mim_impact_std'] = result['impact_std']
        features['mim_impact_volatility'] = result['impact_volatility']
        features['mim_impact_predictability'] = result['impact_predictability']
        features['mim_optimal_size'] = result['optimal_size']
        features['mim_impact_cost'] = result['impact_cost']
        features['mim_impact_cost_smooth'] = result['impact_cost_smooth']
        features['mim_low_impact'] = result['low_impact']
        features['mim_high_impact'] = result['high_impact']
        features['mim_optimal_conditions'] = result['optimal_conditions']
        features['mim_impact_efficiency'] = result['impact_efficiency']
        
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

