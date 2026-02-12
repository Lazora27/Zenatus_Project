import os
import sys
from pathlib import Path

BASE = Path(os.environ.get("ZENATUS_BASE_PATH", "/opt/Zenatus_Backtester"))

KEYWORDS = [
    "zenatus",
    "root",
    "path",
    "base_path",
    "zenatus_base_path",
    "base = path",
]

TARGET_EXTS = {".py", ".ps1", ".bat", ".cmd", ".sh", ".json", ".ini", ".cfg"}

REWRITE_MAP = {
    r"D:\2_Trading\Zenatus\Zenatus_Backtester": "/opt/Zenatus_Backtester",
    r"d:\2_Trading\Zenatus\Zenatus_Backtester": "/opt/Zenatus_Backtester",
    r"D:/2_Trading/Zenatus/Zenatus_Backtester": "/opt/Zenatus_Backtester",
    r"d:/2_Trading/Zenatus/Zenatus_Backtester": "/opt/Zenatus_Backtester",
    r"D:\2_Trading\Zenatus\Zenatus_Dokumentation": "/opt/Zenatus_Dokumentation",
    r"d:\2_Trading\Zenatus\Zenatus_Dokumentation": "/opt/Zenatus_Dokumentation",
    r"D:/2_Trading/Zenatus/Zenatus_Dokumentation": "/opt/Zenatus_Dokumentation",
    r"d:/2_Trading/Zenatus/Zenatus_Dokumentation": "/opt/Zenatus_Dokumentation",
    # Legacy Project Names
    r"D:\2_Trading\Superindikator_Alpha": "/opt/Zenatus_Backtester",
    r"D:\2_Trading\Superindikator_Gamma": "/opt/Zenatus_Backtester",
    r"D:/2_Trading/Superindikator_Alpha": "/opt/Zenatus_Backtester",
    r"D:/2_Trading/Superindikator_Gamma": "/opt/Zenatus_Backtester",
}


def iter_files(root: Path):
    # Scan ALL directories, including venv and Archive
    skip_dirs = {"__pycache__", ".git", ".idea", ".vscode"} 
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        dp = Path(dirpath)
        for name in filenames:
            # Skip obvious binaries to avoid corruption
            if name.lower().endswith(('.exe', '.dll', '.so', '.pyc', '.pyd', '.zip', '.tar', '.gz')):
                continue
            yield dp / name


def find_matches():
    results = []
    lower_keywords = [k.lower() for k in KEYWORDS]
    for fp in iter_files(BASE):
        if fp.name == "pathfinder_agent.py":
            continue
        try:
            # Read as text, skipping binaries that fail decoding check if strict
            # but using errors='ignore' allows reading mixed content. 
            # We'll rely on extension filtering above for safety.
            with fp.open("r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, 1):
                    lower = line.lower()
                    hits = [k for k in lower_keywords if k in lower]
                    if hits:
                        results.append((fp, idx, hits, line.rstrip()))
        except:
            continue
    return results


def format_result(base: Path, file_path: Path, line_no: int, words, text: str):
    try:
        rel = file_path.relative_to(base)
    except ValueError:
        rel = file_path
    unique_words = sorted(set(words))
    kw = ", ".join(unique_words)
    snippet = text.strip()
    if len(snippet) > 200:
        snippet = snippet[:197] + "..."
    return f"Gefunden in {rel}, Zeile {line_no}, Schlüsselwort(er): {kw} | {snippet}"


def rewrite_paths():
    changed_files = 0
    total_replacements = 0
    for fp in iter_files(BASE):
        # Scan ALL files, no directory exclusions (iter_files handles binaries/hidden dirs)
        if fp.name == "pathfinder_agent.py":
            continue
            
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except:
            continue
        new_text = text
        replacements_here = 0
        for old, new in REWRITE_MAP.items():
            if old in new_text:
                new_text = new_text.replace(old, new)
                replacements_here += text.count(old)
        if replacements_here > 0 and new_text != text:
            try:
                fp.write_text(new_text, encoding="utf-8")
                changed_files += 1
                total_replacements += replacements_here
                print(f"Umgeschrieben: {fp} ({replacements_here} Ersetzungen)")
            except:
                continue
    print(f"Pfad-Rewrite abgeschlossen. Dateien geändert: {changed_files}, Ersetzungen gesamt: {total_replacements}")


def main():
    mode = "scan"
    if len(sys.argv) > 1 and sys.argv[1] == "--rewrite":
        mode = "rewrite"
    if mode == "rewrite":
        rewrite_paths()
        return
    matches = find_matches()
    if not matches:
        print("Keine relevanten Pfade oder Schlüsselwörter gefunden.")
        return
    for fp, line_no, words, text in matches:
        print(format_result(BASE, fp, line_no, words, text))


if __name__ == "__main__":
    main()
