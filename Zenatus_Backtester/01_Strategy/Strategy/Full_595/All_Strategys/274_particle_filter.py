"""274 - Particle Filter"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ParticleFilter:
    """Particle Filter - Monte Carlo Localization"""
    PARAMETERS = {
        'num_particles': {'default': 100, 'values': [50,100,200], 'optimize': True},
        'process_noise': {'default': 0.1, 'values': [0.05,0.1,0.2], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ParticleFilter", "Statistics", __version__
    
    def calculate(self, data, params):
        num_particles = params.get('num_particles', 100)
        process_noise = params.get('process_noise', 0.1)
        close = data['close']
        
        # Simplified Particle Filter (using mean of particles)
        filtered = pd.Series(0.0, index=close.index)
        uncertainty = pd.Series(0.0, index=close.index)
        
        # Initialize particles around first value
        if not pd.isna(close.iloc[0]):
            particles = np.random.normal(close.iloc[0], process_noise, num_particles)
        else:
            particles = np.zeros(num_particles)
        
        for i in range(len(close)):
            if pd.isna(close.iloc[i]):
                filtered.iloc[i] = np.mean(particles)
                uncertainty.iloc[i] = np.std(particles)
                continue
            
            # Predict: Add process noise
            particles += np.random.normal(0, process_noise, num_particles)
            
            # Update: Weight particles by likelihood
            weights = np.exp(-0.5 * ((particles - close.iloc[i]) ** 2) / (process_noise ** 2))
            weights /= (weights.sum() + 1e-10)
            
            # Resample
            indices = np.random.choice(num_particles, num_particles, p=weights)
            particles = particles[indices]
            
            filtered.iloc[i] = np.mean(particles)
            uncertainty.iloc[i] = np.std(particles)
        
        above_filtered = (close > filtered).astype(int)
        
        return pd.DataFrame({
            'filtered': filtered,
            'uncertainty': uncertainty,
            'above_filtered': above_filtered
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        pf_data = self.calculate(data, params)
        entries = (data['close'] > pf_data['filtered']) & (data['close'].shift(1) <= pf_data['filtered'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 / (pf_data['uncertainty'] + 1)).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        pf_data = self.calculate(data, params)
        entries = (data['close'] > pf_data['filtered']) & (data['close'].shift(1) <= pf_data['filtered'].shift(1))
        exits = (data['close'] < pf_data['filtered']) & (data['close'].shift(1) >= pf_data['filtered'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_filtered', index=data.index),
                'signal_strength': (1 / (pf_data['uncertainty'] + 1)).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
