"""
INDICATOR DUPLICATE ANALYZER
Analysiert alle 595 Indikatoren und findet identische/ähnliche Implementierungen
"""

import sys
from pathlib import Path
import importlib.util
import inspect
import hashlib
import json

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Production_595_Ultimate"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"

def get_function_source(func):
    """Extrahiere Quellcode einer Funktion"""
    try:
        return inspect.getsource(func)
    except:
        return ""

def analyze_indicator(ind_file):
    """Analysiere einen Indikator und extrahiere wichtige Informationen"""
    ind_name = ind_file.stem
    
    try:
        ind_num = int(ind_name.split('_')[0])
    except:
        return None
    
    try:
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Finde Indicator-Klasse
        class_name = None
        for attr in dir(module):
            if attr.startswith('Indicator_'):
                class_name = attr
                break
        
        if not class_name:
            return None
        
        ind_class = getattr(module, class_name)
        ind_instance = ind_class()
        
        # Extrahiere wichtige Informationen
        info = {
            'num': ind_num,
            'name': ind_name,
            'class_name': class_name,
            'category': getattr(ind_instance, 'category', 'Unknown'),
            'description': getattr(ind_instance, 'name', ind_name),
        }
        
        # Extrahiere calculate() Funktion
        if hasattr(ind_instance, 'calculate'):
            calc_source = get_function_source(ind_instance.calculate)
            # Hash für Vergleich
            info['calc_hash'] = hashlib.md5(calc_source.encode()).hexdigest()
            info['calc_lines'] = len(calc_source.split('\n'))
            
            # Extrahiere Schlüsselwörter aus Code
            keywords = []
            if 'np.sum' in calc_source or 'sum(' in calc_source:
                keywords.append('sum')
            if 'rolling' in calc_source:
                keywords.append('rolling')
            if 'ewm' in calc_source:
                keywords.append('ewm')
            if 'slope' in calc_source:
                keywords.append('linear_regression')
            if 'std' in calc_source or 'stddev' in calc_source:
                keywords.append('stddev')
            if 'mean' in calc_source or 'average' in calc_source:
                keywords.append('mean')
            if 'max' in calc_source or 'min' in calc_source:
                keywords.append('minmax')
            if 'diff' in calc_source:
                keywords.append('diff')
            if 'shift' in calc_source:
                keywords.append('shift')
            if 'cumsum' in calc_source:
                keywords.append('cumsum')
            
            info['keywords'] = keywords
        else:
            info['calc_hash'] = None
            info['calc_lines'] = 0
            info['keywords'] = []
        
        # Extrahiere PARAMETERS
        if hasattr(ind_instance, 'PARAMETERS'):
            params = ind_instance.PARAMETERS
            info['parameters'] = list(params.keys())
            info['param_count'] = len([p for p in params.keys() if p not in ['tp_pips', 'sl_pips']])
        else:
            info['parameters'] = []
            info['param_count'] = 0
        
        return info
        
    except Exception as e:
        print(f"[ERROR] {ind_name}: {str(e)[:100]}")
        return None

def find_duplicates(indicators_info):
    """Finde Duplikate basierend auf calc_hash"""
    hash_groups = {}
    
    for info in indicators_info:
        if info['calc_hash']:
            h = info['calc_hash']
            if h not in hash_groups:
                hash_groups[h] = []
            hash_groups[h].append(info)
    
    # Finde Gruppen mit mehr als 1 Indikator
    duplicates = []
    for h, group in hash_groups.items():
        if len(group) > 1:
            duplicates.append({
                'hash': h,
                'count': len(group),
                'indicators': [{'num': i['num'], 'name': i['name'], 'description': i['description']} for i in group]
            })
    
    return duplicates

def find_similar_by_keywords(indicators_info):
    """Finde ähnliche Indikatoren basierend auf Keywords"""
    keyword_groups = {}
    
    for info in indicators_info:
        if info['keywords']:
            key = tuple(sorted(info['keywords']))
            if key not in keyword_groups:
                keyword_groups[key] = []
            keyword_groups[key].append(info)
    
    # Finde Gruppen mit mehr als 2 Indikatoren
    similar = []
    for key, group in keyword_groups.items():
        if len(group) > 2:
            similar.append({
                'keywords': list(key),
                'count': len(group),
                'indicators': [{'num': i['num'], 'name': i['name'], 'description': i['description']} for i in group]
            })
    
    return similar

def main():
    print("="*80)
    print("INDICATOR DUPLICATE ANALYZER")
    print("="*80)
    
    all_indicators = sorted(INDICATORS_PATH.glob("*.py"))
    print(f"\nFound {len(all_indicators)} indicator files")
    
    print("\nAnalyzing indicators...")
    indicators_info = []
    
    for i, ind_file in enumerate(all_indicators, 1):
        info = analyze_indicator(ind_file)
        if info:
            indicators_info.append(info)
        
        if i % 50 == 0:
            print(f"  Processed {i}/{len(all_indicators)}...")
    
    print(f"\nSuccessfully analyzed: {len(indicators_info)} indicators")
    
    # Finde exakte Duplikate
    print("\n" + "="*80)
    print("FINDING EXACT DUPLICATES (same calc_hash)...")
    print("="*80)
    
    duplicates = find_duplicates(indicators_info)
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate groups:")
        for dup in duplicates:
            print(f"\n  Group ({dup['count']} indicators):")
            for ind in dup['indicators']:
                print(f"    #{ind['num']:03d} {ind['name']:40s} | {ind['description']}")
    else:
        print("\nNo exact duplicates found")
    
    # Finde ähnliche Indikatoren
    print("\n" + "="*80)
    print("FINDING SIMILAR INDICATORS (same keywords)...")
    print("="*80)
    
    similar = find_similar_by_keywords(indicators_info)
    
    if similar:
        print(f"\nFound {len(similar)} similar groups:")
        for sim in similar:
            print(f"\n  Keywords: {', '.join(sim['keywords'])} ({sim['count']} indicators)")
            for ind in sim['indicators'][:10]:  # Nur erste 10 zeigen
                print(f"    #{ind['num']:03d} {ind['name']:40s} | {ind['description']}")
            if sim['count'] > 10:
                print(f"    ... and {sim['count'] - 10} more")
    
    # Speichere vollständige Analyse
    output_file = OUTPUT_PATH / "INDICATOR_ANALYSIS_COMPLETE.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_indicators': len(indicators_info),
            'exact_duplicates': duplicates,
            'similar_groups': similar,
            'all_indicators': indicators_info
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Complete analysis saved to: {output_file}")
    print(f"{'='*80}")
    
    # Erstelle einfache Duplikate-Liste
    if duplicates:
        skip_list = []
        for dup in duplicates:
            # Behalte den ersten, skippe den Rest
            inds = sorted(dup['indicators'], key=lambda x: x['num'])
            for ind in inds[1:]:
                skip_list.append(ind['num'])
        
        skip_file = OUTPUT_PATH / "SKIP_INDICATORS_DUPLICATES.txt"
        with open(skip_file, 'w', encoding='utf-8') as f:
            f.write("# DUPLICATE INDICATORS TO SKIP\n")
            f.write(f"# Total: {len(skip_list)} duplicates found\n\n")
            f.write("SKIP_INDICATORS = [\n")
            for num in sorted(skip_list):
                f.write(f"    {num},\n")
            f.write("]\n")
        
        print(f"\nSkip list saved to: {skip_file}")
        print(f"Total duplicates to skip: {len(skip_list)}")
        print(f"Unique indicators: {len(indicators_info) - len(skip_list)}")

if __name__ == "__main__":
    main()
