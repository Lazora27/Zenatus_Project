# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# CONFIG
# In Docker, we mount the repo to /app (which is the parent of ZENATUS_BASE_PATH=/app/Zenatus_Backtester)
# But wait, config says ZENATUS_BASE_PATH=/opt/Zenatus_Backtester on host.
# Inside docker: /app/Zenatus_Backtester.
# We need to find the .git folder.

def find_repo_root():
    # Try current working directory and parents
    current = Path.cwd()
    for _ in range(4):
        if (current / ".git").exists():
            return current
        current = current.parent
    
    # Try config or env var
    env_base = os.environ.get("ZENATUS_BASE_PATH")
    if env_base:
        p = Path(env_base)
        if (p / ".git").exists(): return p
        if (p.parent / ".git").exists(): return p.parent
        
    # Fallback to standard locations
    if Path("/app/.git").exists(): return Path("/app")
    if Path("/opt/.git").exists(): return Path("/opt")
    
    return None

REPO_ROOT = find_repo_root()

def run_cmd(cmd, cwd=None):
    try:
        subprocess.run(cmd, check=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[GIT-SYNC] Error running {' '.join(cmd)}: {e.stderr.decode('utf-8', errors='ignore')}")
        return False

def git_sync():
    if not REPO_ROOT:
        print("[GIT-SYNC] Error: Could not find .git repository root.")
        return

    print(f"[GIT-SYNC] Starting synchronization in {REPO_ROOT}...")
    
    # 1. Add all changes
    if not run_cmd(["git", "add", "."], cwd=REPO_ROOT):
        return

    # 2. Check if there are changes to commit
    status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, stdout=subprocess.PIPE)
    if not status_proc.stdout.strip():
        print("[GIT-SYNC] No changes to commit.")
        return

    # 3. Commit
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"Auto-Sync: Pipeline Results {ts}"
    if not run_cmd(["git", "commit", "-m", msg], cwd=REPO_ROOT):
        return

    # 4. Push
    # Try pushing; if it fails (e.g. non-fast-forward), try pull --rebase then push
    print("[GIT-SYNC] Pushing to remote...")
    if not run_cmd(["git", "push"], cwd=REPO_ROOT):
        print("[GIT-SYNC] Push failed. Trying pull --rebase...")
        if run_cmd(["git", "pull", "--rebase"], cwd=REPO_ROOT):
            run_cmd(["git", "push"], cwd=REPO_ROOT)

    print("[GIT-SYNC] Synchronization complete.")

if __name__ == "__main__":
    git_sync()
