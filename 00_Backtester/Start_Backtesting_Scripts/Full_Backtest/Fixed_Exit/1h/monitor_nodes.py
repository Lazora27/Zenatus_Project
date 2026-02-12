import time
import glob
import os
import re

LOG_DIR = "/opt/Zenatus_Dokumentation/LOG/1h/nodes"

def tail_f_all():
    print(f"Monitoring logs in {LOG_DIR}...")
    print("Waiting for updates... (Ctrl+C to stop)")
    
    files = glob.glob(os.path.join(LOG_DIR, "*.stdout.log"))
    if not files:
        print("No log files found yet.")
        return

    # Open all files
    f_handles = {f: open(f, 'r') for f in files}
    
    # Seek to end initially? No, user wants to see what happened.
    # But if files are huge, might be annoying. 
    # Let's read the last few lines of each to start.
    for name, f in f_handles.items():
        # simple tail approach
        lines = f.readlines()
        for line in lines[-5:]: # Show last 5 lines context
             if "[" in line and "]" in line: # Simple filter for formatted lines
                print(f"{os.path.basename(name)}: {line.strip()}")
        # seek to end
        f.seek(0, 2)

    try:
        while True:
            updated = False
            for name, f in f_handles.items():
                line = f.readline()
                while line:
                    if line.strip():
                        # Optional: Filter only lines starting with timestamp [
                        if line.strip().startswith("["):
                            print(f"{line.strip()}")
                        # else:
                        #    print(f"RAW: {line.strip()}")
                    line = f.readline()
                    updated = True
            
            if not updated:
                time.sleep(0.5)
            
            # Check for new files? (Optional, if nodes restart)
            
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    finally:
        for f in f_handles.values():
            f.close()

if __name__ == "__main__":
    tail_f_all()
