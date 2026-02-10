import os
import json
from pathlib import Path

BASE = Path("/opt/Zenatus_Backtester")
DOC = Path("/opt/Zenatus_Dokumentation")
LOG_DIR = DOC / "LOG" / "1h"
LISTING_DIR = DOC / "Listing"
AGENT_LOG_DIR = DOC / "LOG" / "Agent"

def ensure_env():
    os.environ["ZENATUS_BASE_PATH"] = str(BASE)

def truncate_logs():
    files = [
        LOG_DIR / "indicators_all.log",
        LOG_DIR / "indicators_errors.log",
        LOG_DIR / "indicators_no_results.log",
        LOG_DIR / "indicators_successful_backtested.log",
        LOG_DIR / "indicators_timeout.log",
        LOG_DIR / "indicators_warnings.log",
        LOG_DIR / "indicators_working.log",
    ]
    for fp in files:
        if fp.exists():
            try:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write("")
            except:
                pass

def reset_listing():
    payload = {"scripts": []}
    targets = [
        LISTING_DIR / "indicators_working.json",
        LISTING_DIR / "indicators_errors.json",
        LISTING_DIR / "indicators_no_results.json",
        LISTING_DIR / "indicators_warnings.json",
        LISTING_DIR / "indicators_timeout.json",
    ]
    for fp in targets:
        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except:
            pass

def write_last_run():
    try:
        from datetime import datetime
        AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AGENT_LOG_DIR / "last_run.txt", "w", encoding="utf-8") as f:
            f.write(stamp)
    except:
        pass

def main():
    ensure_env()
    truncate_logs()
    reset_listing()
    write_last_run()
    print("SESSION_BOOTSTRAP_DONE")

if __name__ == "__main__":
    main()
