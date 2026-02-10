"""Test warum Indikator-Klassen nicht gefunden werden"""
import sys
import importlib.util
from pathlib import Path

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")

# Teste mehrere Indikatoren
test_indicators = [
    "569_neural_plasticity_indicator.py",
    "588_absolute_dominance_indicator.py", 
    "001_trend_sma.py",
    "100_trend_renko.py"
]

for ind_file_name in test_indicators:
    ind_file = INDICATORS_PATH / ind_file_name
    if not ind_file.exists():
        print(f"❌ {ind_file_name} - FILE NOT FOUND")
        continue
    
    ind_name = ind_file.stem
    
    try:
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Suche Klasse
        class_name = None
        all_classes = []
        for attr in dir(module):
            if not attr.startswith('_'):
                obj = getattr(module, attr)
                if isinstance(obj, type):  # Ist es eine Klasse?
                    all_classes.append(attr)
                    if attr.startswith('Indicator_') or attr.endswith('Indicator'):
                        class_name = attr
                        break
        
        if class_name:
            print(f"✅ {ind_file_name} - FOUND: {class_name}")
        else:
            print(f"⚠️  {ind_file_name} - NO MATCH (Classes: {all_classes})")
            
    except Exception as e:
        print(f"❌ {ind_file_name} - ERROR: {str(e)[:100]}")

print("\n" + "="*80)
print("ANALYSE ABGESCHLOSSEN")
