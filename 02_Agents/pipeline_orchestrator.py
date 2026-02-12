import os
import sys
import subprocess
from pathlib import Path
from config_loader import config
from logger_setup import logger

BASE = config.paths.get("base")
DOC = config.paths.get("documentation")
VENV_SITE = BASE / "Zenatus_Backtest_venv" / "Lib" / "site-packages"
VENV_ROOT = BASE / "Zenatus_Backtest_venv"

FIXED_1H = BASE / "00_Backtester" / "Start_Backtesting_Scripts" / "Full_Backtest" / "Fixed_Exit" / "1h"
SCRIPT_QUICK = FIXED_1H / "QUICKTEST_1H_FIRST_RUN_595.py"
SCRIPT_ADAPTIVE360 = FIXED_1H / "PRODUCTION_1H_ADAPTIVE_360.py"
SCRIPT_ADAPTIVE = FIXED_1H / "PRODUCTION_1H_ADAPTIVE.py"

LISTING = {
    "WORKING": config.paths.get("listings") / "indicators_working.json",
    "ERROR": config.paths.get("listings") / "indicators_errors.json",
    "NO_RESULTS": config.paths.get("listings") / "indicators_no_results.json",
    "WARNING": config.paths.get("listings") / "indicators_warnings.json",
    "TIMEOUT": config.paths.get("listings") / "indicators_timeout.json",
}

def get_venv_python():
    candidates = []
    candidates.append(VENV_ROOT / "bin" / "python")
    candidates.append(VENV_ROOT / "Scripts" / "python.exe")
    for c in candidates:
        try:
            if c.exists():
                return str(c)
        except:
            continue
    return None

def ensure_env():
    os.environ["ZENATUS_BASE_PATH"] = str(BASE)
    if VENV_SITE.exists():
        sys.path.insert(0, str(VENV_SITE))
    vp = get_venv_python()
    if vp:
        os.environ["VIRTUAL_ENV"] = str(VENV_ROOT)
        path_parts = [str(Path(vp).parent)]
        try:
            path_parts.append(os.environ.get("PATH", ""))
        except:
            pass
        os.environ["PATH"] = os.pathsep.join([p for p in path_parts if p])

def run_py(fp, args=None):
    vp = get_venv_python()
    try:
        if vp and vp.lower().endswith(".exe") and os.name != "nt":
            vp = None
    except:
        vp = None
    pybin = vp if vp else sys.executable
    cmd = [pybin, str(fp)]
    if args:
        cmd += args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    sys.stdout.write(out.decode("utf-8", errors="ignore"))
    sys.stdout.write(err.decode("utf-8", errors="ignore"))
    return p.returncode

def run_bootstrap():
    fp = BASE / "02_Agents" / "session_bootstrap.py"
    return run_py(fp)

def run_log_sync():
    fp = BASE / "02_Agents" / "log_listening_sync.py"
    return run_py(fp)

def run_tree_agent():
    fp = BASE / "02_Agents" / "tree_agent_enhanced.py"
    return run_py(fp)

def run_git_sync():
    fp = BASE / "02_Agents" / "git_sync_agent.py"
    return run_py(fp)

def run_cleanup():
    fp = BASE / "02_Agents" / "cleanup_agent.py"
    return run_py(fp)

def run_quicktest_validate_all(timeout_sec=900, limit=None, workers=0):
    args = ["--validate-all", "--timeout-sec", str(timeout_sec)]
    if limit is not None:
        args += ["--limit", str(limit)]
    if workers and workers > 0:
        args += ["--workers", str(workers)]
    rc = run_py(SCRIPT_QUICK, args)
    run_log_sync()
    run_git_sync()
    return rc

def run_production_adaptive360():
    rc = run_py(SCRIPT_ADAPTIVE360, [])
    run_log_sync()
    return rc

def run_production_adaptive():
    rc = run_py(SCRIPT_ADAPTIVE, [])
    run_log_sync()
    return rc

def load_listing(fp):
    try:
        import json
        data = json.load(open(fp, "r", encoding="utf-8"))
        return data.get("scripts", [])
    except:
        return []

def run_category(category):
    items = load_listing(LISTING[category])
    for name in items:
        sys.stdout.write(f"{category}:{name}\n")
    return 0

def main():
    ensure_env()
    # run_bootstrap() # DISABLED to allow resuming from checkpoint
    mode = os.environ.get("ZENATUS_PIPELINE_MODE", "QUICKTEST")
    if mode == "QUICKTEST":
        # Removed limit to allow full run (resume logic in script will handle skipping)
        run_quicktest_validate_all(timeout_sec=600, limit=None, workers=4)
    elif mode == "ADAPTIVE360":
        run_production_adaptive360()
    elif mode == "ADAPTIVE":
        run_production_adaptive()
    elif mode in LISTING.keys():
        run_category(mode)
    else:
        run_log_sync()
    try:
        run_tree_agent()
    except:
        pass
    
    # Maintenance
    try:
        run_cleanup()
    except:
        pass

    # Final sync at end of loop
    run_git_sync()
    sys.stdout.write("PIPELINE_DONE\n")

if __name__ == "__main__":
    main()
