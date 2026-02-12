import json
from pathlib import Path

DOC = Path("/opt/Zenatus_Dokumentation")
LOG_DIR = DOC / "LOG" / "1h"
LISTING_DIR = DOC / "Listing"

MAP = {
    "indicators_working.json": LOG_DIR / "indicators_successful_backtested.log",
    "indicators_errors.json": LOG_DIR / "indicators_errors.log",
    "indicators_no_results.json": LOG_DIR / "indicators_no_results.log",
    "indicators_warnings.json": LOG_DIR / "indicators_warnings.log",
    "indicators_timeout.json": LOG_DIR / "indicators_timeout.log",
}

def read_indicators_from_log(fp: Path):
    inds = set()
    if not fp.exists():
        return inds
    try:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    name = obj.get("indicator")
                    if name:
                        inds.add(name)
                except:
                    continue
    except:
        pass
    return inds

def write_listing(out_fp: Path, items):
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    payload = {"scripts": sorted(set(items))}
    with open(out_fp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main():
    for listing_name, log_fp in MAP.items():
        inds = read_indicators_from_log(log_fp)
        write_listing(LISTING_DIR / listing_name, inds)
    print("LISTENING_SYNC_DONE")

if __name__ == "__main__":
    main()
