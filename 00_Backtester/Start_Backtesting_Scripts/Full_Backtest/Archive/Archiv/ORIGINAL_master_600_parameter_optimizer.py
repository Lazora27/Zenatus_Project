"""
MASTER PARAMETER OPTIMIZER - ALLE 600 INDIKATOREN
Extrahiert alle PARAMETERS und generiert optimierte Kombinationen
Basiert auf mathematischen Formeln: Fibonacci, Primzahlen, Exponentiell
"""

import sys
import json
import math
from pathlib import Path
import importlib.util
from datetime import datetime
from typing import Dict, List, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "02_Indicators" / "Indicator_Scripts_Standard_Ready(GO)"
OUTPUT_PATH = BASE_PATH / "02_Indicators" / "Optimized_Parameters" / "Master_Parameter_Combinations"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

print("="*80)
print("🚀 MASTER PARAMETER OPTIMIZER - 600 INDIKATOREN")
print("="*80)

class MasterParameterOptimizer:
    """Master-System für Parameter-Optimierung aller 600 Indikatoren"""
    
    def __init__(self):
        self.fibonacci_sequence = [1,2,3,5,8,13,21,34,55,89,144,233]
        self.prime_numbers = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97]
        
        # Mathematische Formeln für verschiedene Parameter-Typen
        self.parameter_strategies = {
            'period': self._fibonacci_expansion,
            'length': self._fibonacci_expansion, 
            'window': self._fibonacci_expansion,
            'span': self._fibonacci_expansion,
            
            'multiplier': self._exponential_steps,
            'mult': self._exponential_steps,
            'factor': self._exponential_steps,
            'std': self._exponential_steps,
            'dev': self._exponential_steps,
            
            'threshold': self._linear_interpolation,
            'level': self._linear_interpolation,
            'upper': self._linear_interpolation,
            'lower': self._linear_interpolation,
            'overbought': self._linear_interpolation,
            'oversold': self._linear_interpolation,
            
            'smooth': self._prime_based,
            'alpha': self._decimal_progression,
            'beta': self._decimal_progression,
            
            'fast': self._fibonacci_expansion,
            'slow': self._fibonacci_expansion, 
            'signal': self._fibonacci_expansion,
            
            'tp_pips': self._trading_pips_expansion,
            'sl_pips': self._trading_pips_expansion
        }
    
    def extract_parameters_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Extrahiert PARAMETERS aus Indikator-Datei ohne VectorBT"""
        try:
            # Lese Datei als Text und parse PARAMETERS
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Suche nach PARAMETERS = { ... }
            if 'PARAMETERS = {' not in content:
                return {'success': False, 'error': 'NO_PARAMETERS'}
            
            # Mock VectorBT import um Fehler zu vermeiden
            mock_code = content.replace('import vectorbt as vbt', '# import vectorbt as vbt')
            mock_code = mock_code.replace('from vectorbt', '# from vectorbt')
            
            # Sichere Ausführung in separatem Namespace
            namespace = {
                '__name__': '__main__',
                'pd': None,  # Mock pandas
                'np': None,  # Mock numpy
                'vbt': None, # Mock vectorbt
                'warnings': None,
                'Dict': dict,
                'Tuple': tuple,
                'Optional': type(None)
            }
            
            exec(mock_code, namespace)
            
            # Finde Klasse mit PARAMETERS
            for name, obj in namespace.items():
                if hasattr(obj, 'PARAMETERS') and isinstance(obj.PARAMETERS, dict):
                    return {
                        'success': True,
                        'class_name': name,
                        'parameters': obj.PARAMETERS
                    }
            
            return {'success': False, 'error': 'NO_PARAMETERS'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def _fibonacci_expansion(self, base_config: Dict) -> List[int]:
        """Fibonacci-basierte Expansion für Perioden"""
        default = base_config.get('default', 14)
        min_val = base_config.get('min', 2)
        max_val = base_config.get('max', 100)
        
        # Konvertiere zu numerischen Werten
        try:
            default = float(default) if default is not None else 14
            min_val = float(min_val) if min_val is not None else 2
            max_val = float(max_val) if max_val is not None else 100
        except (ValueError, TypeError):
            default, min_val, max_val = 14, 2, 100
        
        # Fibonacci-Skalierung basierend auf default
        scale_factor = default / 21  # 21 ist mittlerer Fibonacci-Wert
        
        values = set()
        for fib in self.fibonacci_sequence:
            scaled = int(fib * scale_factor)
            if min_val <= scaled <= max_val:
                values.add(scaled)
        
        # Füge Original-Werte hinzu falls vorhanden
        if 'values' in base_config:
            for val in base_config['values']:
                if min_val <= val <= max_val:
                    values.add(val)
        
        return sorted(list(values))
    
    def _exponential_steps(self, base_config: Dict) -> List[float]:
        """Exponentielle Schritte für Multiplikatoren"""
        default = base_config.get('default', 2.0)
        min_val = base_config.get('min', 0.5)
        max_val = base_config.get('max', 5.0)
        
        # Konvertiere zu numerischen Werten
        try:
            default = float(default) if default is not None else 2.0
            min_val = float(min_val) if min_val is not None else 0.5
            max_val = float(max_val) if max_val is not None else 5.0
        except (ValueError, TypeError):
            default, min_val, max_val = 2.0, 0.5, 5.0
        
        # Exponentielle Multiplikatoren
        multipliers = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        
        values = set()
        for mult in multipliers:
            val = default * mult
            if min_val <= val <= max_val:
                values.add(round(val, 2))
        
        return sorted(list(values))
    
    def _linear_interpolation(self, base_config: Dict) -> List[int]:
        """Lineare Interpolation für Schwellwerte"""
        default = base_config.get('default', 50)
        min_val = base_config.get('min', 10)
        max_val = base_config.get('max', 90)
        
        # Konvertiere zu numerischen Werten
        try:
            default = float(default) if default is not None else 50
            min_val = float(min_val) if min_val is not None else 10
            max_val = float(max_val) if max_val is not None else 90
        except (ValueError, TypeError):
            default, min_val, max_val = 50, 10, 90
        
        # 15 gleichmäßig verteilte Werte
        step = (max_val - min_val) / 14
        values = set()
        
        for i in range(15):
            val = int(min_val + i * step)
            values.add(val)
        
        # Original-Werte hinzufügen
        if 'values' in base_config:
            for val in base_config['values']:
                if min_val <= val <= max_val:
                    values.add(val)
        
        return sorted(list(values))
    
    def _prime_based(self, base_config: Dict) -> List[int]:
        """Primzahl-basierte Werte für Glättungs-Parameter"""
        default = base_config.get('default', 3)
        min_val = base_config.get('min', 2)
        max_val = base_config.get('max', 50)
        
        # Konvertiere zu numerischen Werten
        try:
            default = float(default) if default is not None else 3
            min_val = float(min_val) if min_val is not None else 2
            max_val = float(max_val) if max_val is not None else 50
        except (ValueError, TypeError):
            default, min_val, max_val = 3, 2, 50
        
        values = set()
        for prime in self.prime_numbers:
            if min_val <= prime <= max_val:
                values.add(prime)
        
        return sorted(list(values))
    
    def _decimal_progression(self, base_config: Dict) -> List[float]:
        """Dezimal-Progression für Alpha/Beta Werte"""
        default = base_config.get('default', 0.5)
        min_val = base_config.get('min', 0.1)
        max_val = base_config.get('max', 1.0)
        
        # Konvertiere zu numerischen Werten
        try:
            default = float(default) if default is not None else 0.5
            min_val = float(min_val) if min_val is not None else 0.1
            max_val = float(max_val) if max_val is not None else 1.0
        except (ValueError, TypeError):
            default, min_val, max_val = 0.5, 0.1, 1.0
        
        # 0.1, 0.2, 0.3, ... 1.0
        values = []
        current = min_val
        while current <= max_val:
            values.append(round(current, 1))
            current += 0.1
        
        return values
    
    def _trading_pips_expansion(self, base_config: Dict) -> List[int]:
        """Spezielle Expansion für Trading-Pips (TP/SL)"""
        default = base_config.get('default', 50)
        min_val = base_config.get('min', 10)
        max_val = base_config.get('max', 200)
        
        # Konvertiere zu numerischen Werten
        try:
            default = float(default) if default is not None else 50
            min_val = float(min_val) if min_val is not None else 10
            max_val = float(max_val) if max_val is not None else 200
        except (ValueError, TypeError):
            default, min_val, max_val = 50, 10, 200
        
        # Trading-optimierte Werte
        base_values = [10,15,20,25,30,35,40,50,60,75,100,125,150,200]
        
        values = set()
        for val in base_values:
            if min_val <= val <= max_val:
                values.add(val)
        
        return sorted(list(values))
    
    def generate_parameter_combinations(self, indicator_name: str, parameters: Dict) -> Dict[str, Any]:
        """Generiert alle Parameter-Kombinationen für einen Indikator"""
        
        expanded_params = {}
        total_combinations = 1
        
        for param_name, param_config in parameters.items():
            # Bestimme Strategie basierend auf Parameter-Namen
            strategy = None
            param_lower = param_name.lower()
            
            for keyword, strategy_func in self.parameter_strategies.items():
                if keyword in param_lower:
                    strategy = strategy_func
                    break
            
            # Fallback: Fibonacci für unbekannte Parameter
            if strategy is None:
                strategy = self._fibonacci_expansion
            
            # Generiere Werte
            expanded_values = strategy(param_config)
            expanded_params[param_name] = {
                'original_config': param_config,
                'expanded_values': expanded_values,
                'count': len(expanded_values)
            }
            
            total_combinations *= len(expanded_values)
        
        return {
            'indicator': indicator_name,
            'parameters': expanded_params,
            'total_combinations': total_combinations,
            'generation_timestamp': datetime.now().isoformat()
        }
    
    def process_all_indicators(self):
        """Verarbeitet alle 600 Indikatoren"""
        
        indicator_files = sorted(list(INDICATORS_PATH.glob("*.py")))
        indicator_files = [f for f in indicator_files if not f.name.startswith('_')]
        
        print(f"📦 Verarbeite {len(indicator_files)} Indikatoren...")
        print("-" * 80)
        
        results = {
            'metadata': {
                'total_indicators': len(indicator_files),
                'processed_successfully': 0,
                'failed': 0,
                'processing_date': datetime.now().isoformat(),
                'total_combinations_all': 0
            },
            'indicators': {}
        }
        
        for i, file_path in enumerate(indicator_files, 1):
            indicator_name = file_path.stem
            
            print(f"[{i:3d}/{len(indicator_files)}] {indicator_name:<50}", end=" ")
            
            # Extrahiere Parameter
            extraction_result = self.extract_parameters_from_file(file_path)
            
            if extraction_result['success']:
                # Generiere Kombinationen
                combinations = self.generate_parameter_combinations(
                    indicator_name, 
                    extraction_result['parameters']
                )
                
                results['indicators'][indicator_name] = combinations
                results['metadata']['total_combinations_all'] += combinations['total_combinations']
                results['metadata']['processed_successfully'] += 1
                
                print(f"✅ {combinations['total_combinations']:,} Kombinationen")
                
                # Speichere einzelne Datei
                output_file = OUTPUT_PATH / f"{indicator_name}_parameters.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(combinations, f, indent=2, ensure_ascii=False)
                
            else:
                results['indicators'][indicator_name] = {
                    'error': extraction_result['error'],
                    'status': 'FAILED'
                }
                results['metadata']['failed'] += 1
                print(f"❌ {extraction_result['error']}")
        
        # Speichere Master-Handbuch
        master_file = OUTPUT_PATH / "MASTER_PARAMETERS_HANDBOOK.json"
        with open(master_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*80)
        print(f"✅ Erfolgreich: {results['metadata']['processed_successfully']}")
        print(f"❌ Fehler: {results['metadata']['failed']}")
        print(f"📊 Gesamt-Kombinationen: {results['metadata']['total_combinations_all']:,}")
        print(f"📚 Master-Handbuch: {master_file}")
        print(f"📁 Einzeldateien: {OUTPUT_PATH}")
        print("="*80)
        
        return results

def main():
    optimizer = MasterParameterOptimizer()
    optimizer.process_all_indicators()

if __name__ == "__main__":
    main()