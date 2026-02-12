import time
import glob
import os
import json
import math
from pathlib import Path
from datetime import datetime

# CONFIG
CHECKPOINT_DIR = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/30m/00_checkpoint")

def format_runtime(start_ts):
    if not start_ts: return "00H 00M 00S"
    elapsed = time.time() - start_ts
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    return f"{h:02d}H {m:02d}M {s:02d}S"

def clear_screen():
    print("\033[H\033[J", end="")

def monitor_checkpoints():
    print(f"Monitoring checkpoints in {CHECKPOINT_DIR}...")
    
    # Store previous states to detect changes
    last_states = {}
    
    try:
        while True:
            # 1. Read all checkpoint files
            files = sorted(glob.glob(str(CHECKPOINT_DIR / "worker_*_checkpoint.json")))
            
            if not files:
                print("No checkpoint files found yet. Waiting...")
                time.sleep(5)
                continue
                
            clear_screen()
            print(f"=== BACKTEST MONITOR (30m) - {datetime.now().strftime('%H:%M:%S')} ===")
            print("-" * 80)
            
            # 2. Process each worker
            for fpath in files:
                try:
                    # Parse worker ID from filename: worker_X_checkpoint.json
                    fname = os.path.basename(fpath)
                    worker_id = fname.split("_")[1]
                    
                    with open(fpath, "r") as f:
                        data = json.load(f)
                        
                    # Extract Data
                    strat_num = data.get("strategy_num", "???")
                    strat_name = data.get("strategy_name", "Unknown")
                    start_ts = data.get("start_time", 0)
                    curr = data.get("current_combo", 0)
                    total = data.get("total_combos", 0)
                    
                    ret = data.get("best_return", 0.0)
                    dd = data.get("best_dd", 0.0)
                    win = data.get("best_winrate", 0.0)
                    trades = data.get("best_trades", 0)
                    pf = data.get("best_pf", 0.0)
                    sharpe = data.get("best_sharpe", 0.0)
                    
                    # Calculate Progress
                    progress_pct = (curr / total * 100) if total > 0 else 0.0
                    
                    # Print Block
                    print(f"[Worker {worker_id}] Strat: {strat_num} - {strat_name}")
                    print(f"  Runtime:    {format_runtime(start_ts)}")
                    print(f"  Progress:   {curr} / {total} ({progress_pct:.1f}%)")
                    print(f"  Best Run:   Ret: {ret:.2f}% | DD: {dd:.2f}% | WR: {win:.2f}% | Trades: {trades}")
                    print(f"              PF: {pf:.2f} | Sharpe: {sharpe:.2f}")
                    print("-" * 40)
                    
                except Exception as e:
                    # File might be empty/writing
                    pass
            
            # Refresh Rate (User requested 20s updates, but standard monitoring is usually faster)
            # The prompt says: "Every 20 seconds: Read current... Print updated values..."
            # We can sleep 20s.
            time.sleep(20)
            
    except KeyboardInterrupt:
        print("\nMonitor stopped.")

if __name__ == "__main__":
    monitor_checkpoints()
