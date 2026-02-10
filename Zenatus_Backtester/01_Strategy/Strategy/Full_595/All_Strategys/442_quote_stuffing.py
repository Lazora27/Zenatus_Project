"""442 - Quote Stuffing Detection"""
import numpy as np
import pandas as pd

from typing import Dict
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_QuoteStuffing:
    """Quote Stuffing - Detects excessive quote activity (HFT manipulation)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "QuoteStuffing", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Quote activity proxy (price updates without volume)
        price_change = abs(data['close'].diff())
        volume = data['volume']
        
        # Quote-to-trade ratio (high quotes, low trades)
        price_updates = (price_change > 0).astype(int)
        trade_activity = (volume > volume.rolling(period).mean()).astype(int)
        
        # Quote stuffing signature
        quote_count = price_updates.rolling(period).sum()
        trade_count = trade_activity.rolling(period).sum()
        quote_to_trade = quote_count / (trade_count + 1e-10)
        
        # Excessive quoting
        avg_quote_to_trade = quote_to_trade.rolling(50).mean()
        quote_excess = quote_to_trade / (avg_quote_to_trade + 1e-10)
        quote_excess_normalized = quote_excess / quote_excess.rolling(50).max()
        
        # Price stability during quote stuffing
        price_volatility = price_change.rolling(period).std()
        stability = 1 / (price_volatility + 1e-10)
        stability_normalized = stability / stability.rolling(50).max()
        
        # Quote stuffing score
        stuffing_score = quote_excess_normalized * stability_normalized
        stuffing_score_smooth = stuffing_score.rolling(5).mean()
        
        # High stuffing periods
        high_stuffing = stuffing_score_smooth > 0.7
        
        # Market quality degradation
        spread_proxy = data['high'] - data['low']
        avg_spread = spread_proxy.rolling(period).mean()
        spread_widening = spread_proxy / (avg_spread + 1e-10)
        
        # Liquidity impact (stuffing = fake liquidity)
        liquidity_score = 1 / (quote_excess_normalized + 1e-10)
        liquidity_score_normalized = liquidity_score / liquidity_score.rolling(50).max()
        
        # Market health (low stuffing = healthy)
        market_health = liquidity_score_normalized * (1 - stuffing_score_smooth)
        market_health_smooth = market_health.rolling(5).mean()
        
        # Stuffing intensity
        stuffing_intensity = quote_excess_normalized * quote_count / period
        stuffing_intensity_smooth = stuffing_intensity.rolling(5).mean()
        
        # Safe trading conditions
        safe_conditions = (stuffing_score_smooth < 0.4) & (market_health_smooth > 0.6)
        
        return pd.DataFrame({
            'price_updates': price_updates,
            'trade_activity': trade_activity,
            'quote_count': quote_count,
            'trade_count': trade_count,
            'quote_to_trade': quote_to_trade,
            'quote_excess': quote_excess_normalized,
            'stability': stability_normalized,
            'stuffing_score': stuffing_score,
            'stuffing_score_smooth': stuffing_score_smooth,
            'high_stuffing': high_stuffing.astype(int),
            'spread_widening': spread_widening,
            'liquidity_score': liquidity_score_normalized,
            'market_health': market_health,
            'market_health_smooth': market_health_smooth,
            'stuffing_intensity': stuffing_intensity,
            'stuffing_intensity_smooth': stuffing_intensity_smooth,
            'safe_conditions': safe_conditions.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe conditions (no stuffing)
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
        
        # Exit: High stuffing detected
        exits = result['high_stuffing'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('quote_stuffing_detected', index=data.index),
            'signal_strength': result['market_health_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['qs_price_updates'] = result['price_updates']
        features['qs_trade_activity'] = result['trade_activity']
        features['qs_quote_count'] = result['quote_count']
        features['qs_trade_count'] = result['trade_count']
        features['qs_quote_to_trade'] = result['quote_to_trade']
        features['qs_quote_excess'] = result['quote_excess']
        features['qs_stability'] = result['stability']
        features['qs_stuffing_score'] = result['stuffing_score']
        features['qs_stuffing_score_smooth'] = result['stuffing_score_smooth']
        features['qs_high_stuffing'] = result['high_stuffing']
        features['qs_spread_widening'] = result['spread_widening']
        features['qs_liquidity_score'] = result['liquidity_score']
        features['qs_market_health'] = result['market_health']
        features['qs_market_health_smooth'] = result['market_health_smooth']
        features['qs_stuffing_intensity'] = result['stuffing_intensity']
        features['qs_stuffing_intensity_smooth'] = result['stuffing_intensity_smooth']
        features['qs_safe_conditions'] = result['safe_conditions']
        
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

