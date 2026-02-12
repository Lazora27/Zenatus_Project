import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OLD_ROOTS = [
    Path(r"/opt/Zenatus_Backtester"),
    Path(r"/opt/Zenatus_Backtester")
]

MAPPING = {
    r"00_Core\Indicators\Production_595_Ultimate": r"01_Strategy\Strategy\Full_595\All_Strategys",
    r"00_Core\Indicators\Backup_04\Unique": r"01_Strategy\Strategy\Unique\All_Strategys",
    r"00_Core\Indicators\Indicator_Configs": r"01_Strategy\Strategy\Config"
}

# explicit replacements to external documentation roots
EXTERNAL_REPLACEMENTS = [
    (
        str(PROJECT_ROOT / r"00_Backtester\Start_Backtesting_Scripts\Full_Backtest\Documentation\Fixed_Exit\1h"),
        r"/opt/Zenatus_Dokumentation\Dokumentation\Fixed_Exit\1h"
    ),
    (
        str(PROJECT_ROOT / r"00_Backtester\Start_Backtesting_Scripts\Full_Backtest\Outputs"),
        r"/opt/Zenatus_Dokumentation\Dokumentation"
    ),
    (
        str(PROJECT_ROOT / r"00_Backtester\Start_Backtesting_Scripts\Full_Backtest\LOGS"),
        r"/opt/Zenatus_Dokumentation\LOG"
    )
]

TARGET_DIRS = [
    PROJECT_ROOT
]

def ensure_dirs():
    for _, new_rel in MAPPING.items():
        d = PROJECT_ROOT / new_rel
        if str(d).startswith(str(PROJECT_ROOT)):
            d.mkdir(parents=True, exist_ok=True)

def build_replacements(text: str):
    for old_root in OLD_ROOTS:
        old_str = str(old_root).replace("\\", "\\\\")
        text = re.sub(
            r'(BASE_PATH\s*=\s*Path\([rRuU]?[\'"])[^\'"]+([\'"]\))',
            r'\1' + str(PROJECT_ROOT).replace("\\", "\\\\") + r'\2',
            text
        )
        text = re.sub(
            r'(BASE\s*=\s*Path\([rRuU]?[\'"])[^\'"]+([\'"]\))',
            r'\1' + str(PROJECT_ROOT).replace("\\", "\\\\") + r'\2',
            text
        )
        # General root shift: preserve suffix
        text = text.replace(str(old_root) + "\\", str(PROJECT_ROOT) + "\\")
        for old_rel, new_rel in MAPPING.items():
            text = text.replace(str(old_root / old_rel), str(PROJECT_ROOT / new_rel))
            text = text.replace(str(PROJECT_ROOT / old_rel), str(PROJECT_ROOT / new_rel))
        for src, dst in EXTERNAL_REPLACEMENTS:
            text = text.replace(src, dst)
        for old in OLD_ROOTS:
            text = text.replace(str(old), str(PROJECT_ROOT))
    # Explicit parameter optimization files
    text = re.sub(
        r'PARAMETER_HANDBOOK_COMPLETE\.json',
        str(PROJECT_ROOT / r"01_Strategy\Parameter_Optimization\/opt/Zenatus_Backtester\01_Strategy\Parameter_Optimization\/opt/Zenatus_Backtester\01_Strategy\Parameter_Optimization\/opt/Zenatus_Backtester\01_Strategy\Parameter_Optimization\PARAMETER_HANDBOOK_COMPLETE.json").replace("\\", "\\\\"),
        text
    )
    text = re.sub(
        r'PARAMETER_SUMMARY\.csv',
        str(PROJECT_ROOT / r"01_Strategy\Parameter_Optimization\/opt/Zenatus_Backtester\01_Strategy\Parameter_Optimization\/opt/Zenatus_Backtester\01_Strategy\Parameter_Optimization\/opt/Zenatus_Backtester\01_Strategy\Parameter_Optimization\PARAMETER_SUMMARY.csv").replace("\\", "\\\\"),
        text
    )
    return text

def process_file(fp: Path):
    try:
        orig = fp.read_text(encoding="utf-8")
    except:
        return False
    new = build_replacements(orig)
    if new != orig:
        fp.write_text(new, encoding="utf-8")
        return True
    return False

def main():
    ensure_dirs()
    total = 0
    changed = 0
    skip_parts = {"Zenatus_Backtest_venv", "venv", ".git", "__pycache__"}
    for base in TARGET_DIRS:
        for p in base.rglob("*.py"):
            if any(part in str(p) for part in skip_parts):
                continue
            total += 1
            if process_file(p):
                changed += 1
    print(f"Processed {total} files, updated {changed}.")
    print(f"Project root: {PROJECT_ROOT}")

if __name__ == "__main__":
    main()
