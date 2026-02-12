import os
import sys
import subprocess
from pathlib import Path

BASE = Path("/opt/Zenatus_Backtester")
VENV_SITE = BASE / "Zenatus_Backtest_venv" / "Lib" / "site-packages"
SCRIPT = BASE / "00_Backtester" / "Start_Backtesting_Scripts" / "Full_Backtest" / "Fixed_Exit" / "1h" / "QUICKTEST_1H_FIRST_RUN_595.py"

def ensure_env():
    os.environ["ZENATUS_BASE_PATH"] = str(BASE)
    if VENV_SITE.exists():
        sys.path.insert(0, str(VENV_SITE))

def run_quicktest_validate_all(limit=None, timeout_sec=900, workers=0):
    cmd = [sys.executable, str(SCRIPT), "--validate-all", "--timeout-sec", str(timeout_sec)]
    if limit is not None:
        cmd += ["--limit", str(limit)]
    if workers and workers > 0:
        cmd += ["--workers", str(workers)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    print(out.decode("utf-8", errors="ignore"))
    print(err.decode("utf-8", errors="ignore"))
    return p.returncode

def main():
    ensure_env()
    rc = run_quicktest_validate_all(limit=5, timeout_sec=600, workers=4)
    print(f"QUICKTEST_DONE rc={rc}")
    # Sync logs to listening JSONs
    sync = BASE / "02_Agents" / "log_listening_sync.py"
    subprocess.run([sys.executable, str(sync)], check=False)

if __name__ == "__main__":
    main()
