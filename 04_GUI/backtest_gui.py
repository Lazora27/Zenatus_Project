import subprocess
import sys

# ... (Previous Imports)

# --- Path Configurations ---
# Use Environment Variable if available (Local Mode), else default to Docker path
BASE_PATH = os.environ.get("ZENATUS_BASE_PATH", "/app/Zenatus_Backtester")
DOCS_PATH = os.environ.get("ZENATUS_DOCS_PATH", "/app/Zenatus_Dokumentation")

# Adjust paths relative to BASE_PATH
STRATEGY_PATH = os.path.join(BASE_PATH, "01_Strategy/Strategy/Full_595/All_Strategys")
JSON_LISTING_PATH = os.path.join(DOCS_PATH, "Listing")
SPREADS_PATH = os.path.join(BASE_PATH, "00_Backtester/Spreads")
LOGS_PATH = os.path.join(DOCS_PATH, "LOG/1h")

# Runner Script
RUNNER_SCRIPT = os.path.join(BASE_PATH, "00_Backtester/Start_Backtesting_Scripts/Full_Backtest/Fixed_Exit/1h/QUICKTEST_1H_FIRST_RUN_595.py")

# Ensure directories exist
for path in [JSON_LISTING_PATH, SPREADS_PATH, LOGS_PATH]:
    os.makedirs(path, exist_ok=True)

# --- Helper Functions ---
def load_strategy_files(directory):
    # Load .py files directly
    files = glob.glob(os.path.join(directory, "*.py"))
    return [os.path.basename(f) for f in files]

# ... (Previous Helper Functions)

def run_backtest_process(strategy_file, timeframes, capital):
    """
    Runs the actual backtest script via subprocess.
    """
    full_strat_path = os.path.join(STRATEGY_PATH, strategy_file)
    
    cmd = [sys.executable, RUNNER_SCRIPT, full_strat_path]
    
    # Note: The runner script currently takes 'indicator' path as argument.
    # It reads config for other params. 
    # To pass capital/timeframe dynamically, we might need to override config or use env vars.
    # For now, we set ENV vars for the subprocess.
    
    env = os.environ.copy()
    env["ZENATUS_INITIAL_CAPITAL"] = str(capital)
    # env["ZENATUS_TIMEFRAME"] = timeframes[0] # Runner currently handles 1h hardcoded in script, need refactor if dynamic
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    return process

# ... (GUI Layout)

    with st.expander("1. Strategy Selection", expanded=True):
        strategy_source = st.radio("Source", ["All Strategies (.py)", "Listing (JSON)"])
        
        if strategy_source == "All Strategies (.py)":
            strategies = load_strategy_files(STRATEGY_PATH)
            if not strategies:
                st.warning(f"No .py files found in {STRATEGY_PATH}")
                selected_strategy = None
            else:
                selected_strategy = st.selectbox("Select Strategy File", strategies)
        else:
             # ... (JSON logic)
             pass

# ... (Button Logic)

    if col_btn1.button("▶ START BACKTEST"):
        if not selected_strategy:
            st.error("Please select a strategy first.")
        else:
            with st.spinner("Initializing Real Backtest Engine..."):
                # ... (Doc creation logic)
                
                # REAL EXECUTION
                proc = run_backtest_process(selected_strategy, timeframes, capital)
                
                st.session_state['process'] = proc
                st.session_state['status'] = 'RUNNING'
                st.success(f"Started Process PID: {proc.pid}")

    # Live Monitor Real Output
    if st.session_state.get('status') == 'RUNNING':
        proc = st.session_state.get('process')
        if proc:
            # Poll process
            ret = proc.poll()
            if ret is not None:
                st.session_state['status'] = 'FINISHED'
                if ret == 0:
                    st.success("Backtest Finished Successfully!")
                else:
                    st.error(f"Backtest Failed with Exit Code {ret}")
                    st.code(proc.stderr.read())
            else:
                st.info("Backtest Running...")
                # Show last log lines (simulated tail)
                # In real app, we'd need a thread to read stdout without blocking
                st.text("Logs will appear here...")
