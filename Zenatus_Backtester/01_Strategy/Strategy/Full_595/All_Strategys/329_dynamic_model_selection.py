"""329 - Dynamic Model Selection"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DynamicModelSelection:
    """Dynamic Model Selection - Selects best model based on current conditions"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'lookback': {'default': 50, 'values': [30,50,70,100], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DynamicModelSelection", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        lookback = params.get('lookback', 50)
        
        # Define multiple models
        returns = data['close'].pct_change()
        
        # Model 1: Trend following (works in trending markets)
        sma = data['close'].rolling(period).mean()
        model1_pred = (data['close'] > sma).astype(float)
        
        # Model 2: Mean reversion (works in ranging markets)
        zscore = (data['close'] - sma) / (data['close'].rolling(period).std() + 1e-10)
        model2_pred = (zscore < -1).astype(float)
        
        # Model 3: Momentum (works in strong trends)
        momentum = data['close'] - data['close'].shift(10)
        model3_pred = (momentum > 0).astype(float)
        
        # Evaluate recent performance
        future_returns = returns.shift(-1)
        
        model_scores = pd.DataFrame(index=data.index)
        model_scores['model1'] = 0.0
        model_scores['model2'] = 0.0
        model_scores['model3'] = 0.0
        
        selected_model = pd.Series(0, index=data.index)
        dynamic_pred = pd.Series(0.0, index=data.index)
        
        for i in range(lookback, len(data)):
            # Calculate accuracy for each model
            for j, model in enumerate([model1_pred, model2_pred, model3_pred]):
                correct = ((model.iloc[i-lookback:i] > 0.5) == (future_returns.iloc[i-lookback:i] > 0)).sum()
                model_scores.iloc[i, j] = correct / lookback
            
            # Select best model
            best_model = model_scores.iloc[i].values.argmax()
            selected_model.iloc[i] = best_model
            
            # Use selected model's prediction
            if best_model == 0:
                dynamic_pred.iloc[i] = model1_pred.iloc[i]
            elif best_model == 1:
                dynamic_pred.iloc[i] = model2_pred.iloc[i]
            else:
                dynamic_pred.iloc[i] = model3_pred.iloc[i]
        
        # Smooth
        dynamic_smooth = dynamic_pred.rolling(5).mean()
        
        # Selection confidence (score difference)
        score_diff = model_scores.max(axis=1) - model_scores.median(axis=1)
        
        return pd.DataFrame({
            'dynamic_pred': dynamic_pred,
            'dynamic_smooth': dynamic_smooth,
            'selected_model': selected_model,
            'selection_confidence': score_diff
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High dynamic prediction
        entries = result['dynamic_smooth'] > 0.6
        
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
            'signal_strength': result['selection_confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High prediction
        entries = result['dynamic_smooth'] > 0.6
        
        # Exit: Low prediction or model change
        exits = (result['dynamic_smooth'] < 0.4) | (result['selected_model'].diff() != 0)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('model_change', index=data.index),
            'signal_strength': result['selection_confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['dms_pred'] = result['dynamic_pred']
        features['dms_smooth'] = result['dynamic_smooth']
        features['dms_selected_model'] = result['selected_model']
        features['dms_confidence'] = result['selection_confidence']
        features['dms_high_pred'] = (result['dynamic_smooth'] > 0.6).astype(int)
        features['dms_model_stable'] = (result['selected_model'] == result['selected_model'].shift(1)).astype(int)
        
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

