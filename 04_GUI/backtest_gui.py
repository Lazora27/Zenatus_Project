import streamlit as st
import pandas as pd
import os
import json
import subprocess
import uuid
import glob
import sys
from pathlib import Path
from datetime import datetime

# Import Config
# Add agent path to sys.path to import config
sys.path.append(os.path.join(os.environ.get("ZENATUS_BASE_PATH", "/opt/Zenatus_Backtester"), "02_Agents"))
try:
    from config_loader import config
except ImportError:
    # Fallback config
    class ConfigMock:
        def get(self, *args): return None
        @property
        def paths(self): return {}
    config = ConfigMock()

# Config
BASE_PATH = config.paths.get("base") or Path("/opt/Zenatus_Backtester")
# Corrected Strategy Source
STRATEGY_LISTING_BASE = config.paths.get("listings") / "Full_backtest" if config.paths.get("listings") else Path("/opt/Zenatus_Dokumentation/Listing/Full_backtest")
DATA_PATH = config.paths.get("data") or BASE_PATH / "99_Historic_Data"
if not str(DATA_PATH).endswith("Forex/Major"): # Fallback structure fix
     DATA_PATH = DATA_PATH / "Forex" / "Major"
WORKER_SCRIPT = config.paths.get("worker_script") or BASE_PATH / "00_Backtester" / "Start_Backtesting_Scripts" / "Full_Backtest" / "Fixed_Exit" / "1h" / "FULL_BACKTEST_1H_WORKER.py"
RESULTS_BASE = config.paths.get("documentation") / "Dokumentation" / "Fixed_Exit" if config.paths.get("documentation") else Path("/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit")
GUI_DATA_PATH = config.paths.get("gui") / "data" if config.paths.get("gui") else BASE_PATH / "04_GUI" / "data"
GUI_DATA_PATH.mkdir(parents=True, exist_ok=True)
RUN_HISTORY_FILE = GUI_DATA_PATH / "run_history.json"

st.set_page_config(page_title="Zenatus Backtester", layout="wide")

st.title("Zenatus Backtester Interface")

# --- Helper Functions ---
def load_run_history():
    if RUN_HISTORY_FILE.exists():
        try:
            with open(RUN_HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_run_history(history):
    with open(RUN_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_available_strategies(timeframe, statuses):
    """
    Load strategies from /opt/Zenatus_Dokumentation/Listing/Full_backtest/[Timeframe]
    based on status JSON files (e.g. indicators_working.json).
    """
    # Map GUI status to filename suffix
    # Statuses: "Working", "Sucessful", "Warning", "Error", "Timeout", "No_Results"
    # Files: indicators_working.json, indicators_succesful_backtested.json, indicators_warnings.json,
    #        indicators_errors.json, indicators_timeout.json, indicators_no_results.json
    
    status_map = {
        "Working": "indicators_working.json",
        "Sucessful": "indicators_succesful_backtested.json",
        "Warning": "indicators_warnings.json",
        "Error": "indicators_errors.json",
        "Timeout": "indicators_timeout.json",
        "No_Results": "indicators_no_results.json"
    }
    
    listing_path = STRATEGY_LISTING_BASE / timeframe
    if not listing_path.exists():
        # Fallback if specific timeframe folder doesn't exist, maybe default to 1h or check if structure differs
        # User said: "/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h"
        # Let's try to be flexible. If not found for current TF, maybe warn or look in 1h as base?
        # User implied structure exists.
        return []

    all_strategies = set()
    
    for status in statuses:
        filename = status_map.get(status)
        if not filename: continue
        
        filepath = listing_path / filename
        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    # Data format: {"scripts": ["001_trend_sma", ...]}
                    scripts = data.get("scripts", [])
                    all_strategies.update(scripts)
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                
    return sorted(list(all_strategies))

def get_available_symbols():
    """
    Scan /opt/Zenatus_Backtester/99_Historic_Data/Forex/Major
    Exclude *JPY*
    """
    symbols = []
    major_path = DATA_PATH / "Forex" / "Major"
    if major_path.exists():
        # Check subdirectories (timeframes) or symbol directories?
        # Structure seems to be: 99_Historic_Data/Forex/Major/1h/EUR_USD
        # Let's look into 1h folder to get list of symbols, assuming consistent across TFs
        # Or scan recursively.
        # User said: "Die Symbole wären zb EURUSD oder USDCAD bitte alle die wir haebn aus 99_HisData dort erwähnen für Forex Major außer JPY oder JPN"
        
        # Let's scan the '1h' folder inside Major as a proxy for available symbols
        scan_path = major_path / "1h"
        if scan_path.exists():
             for item in scan_path.iterdir():
                 if item.is_dir():
                     sym = item.name
                     if "JPY" not in sym and "JPN" not in sym:
                         symbols.append(sym)
    return sorted(list(set(symbols)))


# --- Sidebar Controls ---
st.sidebar.header("Configuration")

# 0. Timeframe (Moved up as Strategy loading depends on it)
st.sidebar.subheader("Timeframe")
timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
selected_tf = st.sidebar.selectbox("Select Timeframe", timeframes, index=4) # Default 1h

# 1. Strategy Selection
st.sidebar.subheader("Strategy Selection")
status_options = ["Working", "Sucessful", "Warning", "Error", "Timeout", "No_Results"]
selected_statuses = st.sidebar.multiselect("Select Categories", status_options, default=["Working"])

# Load strategies based on TF and Status
strategies = get_available_strategies(selected_tf, selected_statuses)

st.sidebar.write(f"Found {len(strategies)} strategies.")

# Option to select specific strategies or run all
run_all_strategies = st.sidebar.checkbox("Run All Selected Strategies", value=True)

if not run_all_strategies:
    selected_strategies = st.sidebar.multiselect("Select Specific Strategies", strategies)
else:
    selected_strategies = strategies

# 2. Currency Pairs
st.sidebar.subheader("Currency Pairs")
available_symbols = get_available_symbols()
# Default selection
default_symbols = available_symbols[:min(6, len(available_symbols))]
selected_symbols = st.sidebar.multiselect("Select Symbols (Max 6)", available_symbols, default=default_symbols)

if len(selected_symbols) > 6:
    st.sidebar.error("Please select max 6 symbols.")


# 3. Dates
st.sidebar.subheader("Date Range")
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())

# 4. Capital
st.sidebar.subheader("Capital")
capital = st.sidebar.number_input("Starting Capital", value=10000.0, step=1000.0)

# 5. Validation (Optional)
st.sidebar.subheader("Validation (Optional)")
enable_validation = st.sidebar.checkbox("Enable Validation")
if enable_validation:
    wf_ratio = st.sidebar.slider("Walk Forward Ratio", 0.1, 0.9, 0.5)
    ft_ratio = st.sidebar.slider("Forward Test Ratio", 0.1, 0.9, 0.2)


# Run Button
if st.sidebar.button("Run Backtest"):
    if not selected_strategies:
        st.error("No strategies selected.")
    elif len(selected_symbols) > 6:
        st.error("Max 6 symbols allowed.")
    else:
        run_id = str(uuid.uuid4())[:8]
        st.info(f"Starting Backtest Run ID: {run_id}")
        st.info(f"Strategies: {len(selected_strategies)} | TF: {selected_tf}")
        
        # Construct Command
        cmd = [
            "python3", str(WORKER_SCRIPT),
            "--scripts", ",".join(selected_strategies),
            "--timeframe", selected_tf,
            "--symbols", ",".join(selected_symbols),
            "--start-date", start_date.strftime("%Y-%m-%d"),
            "--end-date", end_date.strftime("%Y-%m-%d"),
            "--capital", str(capital)
        ]
        
        # Execute
        try:
            # Using nohup via Popen to detach process
            # We redirect stdout/stderr to files to capture them
            log_dir = GUI_DATA_PATH / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"run_{run_id}.log"
            
            with open(log_file, "w") as f_log:
                # start_new_session=True creates a new process group (setsid), effectively detaching it from the terminal
                process = subprocess.Popen(
                    cmd, 
                    stdout=f_log, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    start_new_session=True 
                )
            
            # Since we detached, we don't wait for communicate() immediately if we want async behavior.
            # But the user wants to see progress? 
            # If we want "Detached and user comes back later", we should NOT wait.
            # But the current UI expects to show logs.
            # Let's Compromise: We show "Started" and let the user check history/logs.
            
            st.success(f"Backtest Started! (PID: {process.pid})")
            st.info("The process is running in the background. You can close the browser and check results later in 'Run History'.")
            
            # Update History
            history = load_run_history()
            history[run_id] = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timeframe": selected_tf,
                "strategies_count": len(selected_strategies),
                "symbols": selected_symbols,
                "status": "Running",
                "pid": process.pid,
                "log_file": str(log_file)
            }
            save_run_history(history)
            
        except Exception as e:
            st.error(f"Execution Error: {e}")

# --- Tabs for Analysis ---
tab1, tab2, tab3 = st.tabs(["Current Results", "Run History", "Settings"])

with tab3:
    st.header("System Configuration")
    config_path = Path("/opt/Zenatus_Backtester/config/config.yaml")
    
    if config_path.exists():
        with open(config_path, "r") as f:
            current_config = f.read()
            
        st.info(f"Editing: {config_path}")
        new_config = st.text_area("config.yaml", current_config, height=600)
        
        if st.button("Save Configuration"):
            try:
                # Basic validation: Check if it's valid YAML
                import yaml
                yaml.safe_load(new_config)
                
                with open(config_path, "w") as f:
                    f.write(new_config)
                st.success("Configuration saved! Restart the container to apply changes.")
            except Exception as e:
                st.error(f"Invalid YAML: {e}")
    else:
        st.error("Config file not found.")

with tab1:
    st.header(f"Results Overview ({selected_tf})")
    
    # Path where results are saved
    results_path = RESULTS_BASE / selected_tf
    
    if results_path.exists():
        all_files = list(results_path.glob("*.csv"))
        
        if all_files:
            st.write(f"Total Result Files: {len(all_files)}")
            
            # Load all data
            data_frames = []
            for f in all_files:
                try:
                    df = pd.read_csv(f)
                    # Filter for top 10 per file/strategy based on Net Profit or Return
                    if not df.empty and "Net_Profit" in df.columns:
                        df_sorted = df.sort_values(by="Net_Profit", ascending=False).head(10)
                        data_frames.append(df_sorted)
                except Exception as e:
                    pass
            
            if data_frames:
                final_df = pd.concat(data_frames, ignore_index=True)
                
                # Columns to show
                cols_to_show = [
                    "Indicator", "Symbol", "Total_Return", "Max_Drawdown", 
                    "Win_Rate_%", "Total_Trades", "Profit_Factor", "Sharpe_Ratio", "Net_Profit"
                ]
                cols_to_show = [c for c in cols_to_show if c in final_df.columns]
                
                st.dataframe(final_df[cols_to_show], use_container_width=True)
                
                # Download
                csv_data = final_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Top 10 Results as CSV",
                    data=csv_data,
                    file_name=f"top10_results_{selected_tf}.csv",
                    mime="text/csv",
                )
                
                st.subheader("Deep Dive")
                selected_deep_dive = st.selectbox("Select Strategy to Inspect", final_df["Indicator"].unique())
                
                if selected_deep_dive:
                    dd_df = final_df[final_df["Indicator"] == selected_deep_dive]
                    st.dataframe(dd_df)
                    
            else:
                st.warning("No valid data found in result files.")
        else:
            st.info("No result files found.")
    else:
        st.info("Results directory does not exist yet.")

def check_pid_running(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

with tab2:
    st.header("Run History")
    
    # Refresh Button
    if st.button("Refresh Status"):
        st.rerun()

    history = load_run_history()
    
    if history:
        # Update Statuses
        updated = False
        for rid, info in history.items():
            if info.get("status") == "Running":
                pid = info.get("pid")
                if pid and not check_pid_running(pid):
                    # Process finished (or died)
                    info["status"] = "Finished (Check Logs)"
                    updated = True
        
        if updated:
            save_run_history(history)
            
        # Convert to DF for display
        hist_df = pd.DataFrame.from_dict(history, orient='index')
        hist_df.index.name = "Run ID"
        hist_df = hist_df.reset_index()
        
        # Display
        st.dataframe(hist_df.sort_values(by="timestamp", ascending=False), use_container_width=True)
        
        # Log Viewer (JSON Enhanced)
        st.subheader("Log Inspector")
        col_log1, col_log2 = st.columns([1, 3])
        
        with col_log1:
            selected_run = st.selectbox("Select Run to View Logs", hist_df["Run ID"].unique())
            
        if selected_run:
            run_info = history.get(selected_run)
            log_file = run_info.get("log_file")
            
            if log_file and os.path.exists(log_file):
                # Try to parse as JSONL if possible, else text
                with open(log_file, "r") as f:
                    content = f.read()
                    
                try:
                    # Attempt to parse line by line as JSON
                    json_logs = []
                    for line in content.splitlines():
                        if not line.strip(): continue
                        try:
                            json_logs.append(json.loads(line))
                        except:
                            # If mixed content, keep as text in a "raw" field
                            json_logs.append({"raw": line})
                    
                    if json_logs:
                        st.info("Structured JSON Logs Detected")
                        log_df = pd.DataFrame(json_logs)
                        # Reorder columns if standard keys exist
                        prio_cols = ["asctime", "levelname", "name", "message"]
                        existing_cols = [c for c in prio_cols if c in log_df.columns]
                        other_cols = [c for c in log_df.columns if c not in prio_cols]
                        
                        # Filter by Level
                        levels = log_df["levelname"].unique() if "levelname" in log_df.columns else []
                        if len(levels) > 0:
                            selected_levels = st.multiselect("Filter Log Level", levels, default=levels)
                            if selected_levels:
                                log_df = log_df[log_df["levelname"].isin(selected_levels)]
                        
                        st.dataframe(log_df[existing_cols + other_cols], use_container_width=True)
                    else:
                        st.text_area("Log Output (Raw)", content, height=400)
                except:
                    st.text_area("Log Output (Raw)", content, height=400)
            else:
                st.warning("Log file not found.")
                
    else:
        st.info("No run history available.")


