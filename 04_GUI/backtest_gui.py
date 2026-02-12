import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import glob

# Page Config
st.set_page_config(
    page_title="Zenatus Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Sexy" Look
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        height: 3em;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- Path Configurations ---
BASE_PATH = "/app/Zenatus_Backtester"
DOCS_PATH = "/app/Zenatus_Dokumentation"
STRATEGY_PATH = os.path.join(DOCS_PATH, "Listing")
SPREADS_PATH = os.path.join(BASE_PATH, "00_Backtester/Spreads")
LOGS_PATH = os.path.join(DOCS_PATH, "LOG/1h")

# Ensure directories exist (for local testing mostly)
for path in [STRATEGY_PATH, SPREADS_PATH, LOGS_PATH]:
    os.makedirs(path, exist_ok=True)

# --- Helper Functions ---
def load_json_files(directory):
    files = glob.glob(os.path.join(directory, "*.json"))
    return [os.path.basename(f) for f in files]

def load_spread_files(directory):
    files = glob.glob(os.path.join(directory, "*.csv")) # Assuming spreads are CSV
    return [os.path.basename(f) for f in files]

def save_test_log(data):
    log_file = os.path.join(BASE_PATH, "04_GUI/Quicktest_GUI_Building.csv")
    df = pd.DataFrame([data])
    if not os.path.exists(log_file):
        df.to_csv(log_file, index=False)
    else:
        df.to_csv(log_file, mode='a', header=False, index=False)

# --- Header ---
st.title("🚀 Zenatus Backtester Machine")
st.markdown("### Advanced Algorithmic Trading Interface")

# --- Layout ---
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("#### ⚙️ Configuration")
    
    with st.expander("1. Strategy Selection", expanded=True):
        strategy_source = st.radio("Source", ["Listing (JSON)", "Logs (History)"])
        
        if strategy_source == "Listing (JSON)":
            strategies = load_json_files(STRATEGY_PATH)
            if not strategies:
                st.warning("No strategy files found in Listing.")
                selected_strategy = "Default_Strategy.json" # Fallback
            else:
                selected_strategy = st.selectbox("Select Strategy File", strategies)
        else:
            # Load from Logs (Mockup based on user request)
            log_files = [
                "indicators_successful_backtested.log",
                "indicators_working.log",
                "indicators_all.log"
            ]
            selected_log = st.selectbox("Select Log File", log_files)
            # Logic to parse log would go here
            selected_strategy = f"Derived from {selected_log}"

    with st.expander("2. Timeframe & Range", expanded=True):
        timeframes = st.multiselect(
            "Timeframes (Batch-Test)",
            options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            default=["1h"]
        )
        
        col_date1, col_date2 = st.columns(2)
        start_date = col_date1.date_input("Start Date", datetime.now() - timedelta(days=365))
        end_date = col_date2.date_input("End Date", datetime.now())

    with st.expander("3. Capital & Risk", expanded=True):
        capital = st.number_input("Starting Capital ($)", value=10000, step=1000)
        
        spreads = load_spread_files(SPREADS_PATH)
        if not spreads:
            spreads = ["Standard_Spreads.csv"] # Fallback
        selected_spread = st.selectbox("Spreads & Fees Model", spreads)

with col2:
    st.markdown("#### 📊 Dashboard & Control")
    
    # Status Board
    st.info(f"**Ready to Backtest:** {selected_strategy} on {timeframe}")
    
    # Action Buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    if col_btn1.button("▶ START BACKTEST"):
        with st.spinner("Initializing Pipeline..."):
            
            # Create Documentation Paths for each Timeframe
            for tf in timeframes:
                # Path: Zenatus_Dokumentation/Dokumentation/[TF]
                doc_dir = os.path.join(DOCS_PATH, "Dokumentation", tf)
                os.makedirs(doc_dir, exist_ok=True)
                
                # CSV File: [StrategyName]_[TF].csv
                # Example: Default_Strategy_1h.csv
                strat_name = os.path.splitext(selected_strategy)[0]
                csv_filename = f"{strat_name}_{tf}.csv"
                csv_path = os.path.join(doc_dir, csv_filename)
                
                # Simulate Writing Initial Header
                if not os.path.exists(csv_path):
                    with open(csv_path, 'w') as f:
                        f.write("Timestamp,Capital,Profit,Drawdown,Winrate,Trades\n")
            
            # Simulate Process
            test_data = {
                "timestamp": datetime.now(),
                "strategy": selected_strategy,
                "timeframes": timeframes,
                "capital": capital,
                "status": "STARTED"
            }
            save_test_log(test_data)
            time.sleep(2) # Mock delay
            st.success(f"Backtest Started! Results will be saved to: {DOCS_PATH}/Dokumentation/[TF]/...")
            st.session_state['status'] = 'RUNNING'
            
    if col_btn2.button("⏸ PAUSE"):
        st.warning("Backtest Paused")
        st.session_state['status'] = 'PAUSED'
        
    if col_btn3.button("⏹ CANCEL"):
        st.error("Backtest Cancelled")
        st.session_state['status'] = 'STOPPED'

    # Live Monitor Mockup
    st.markdown("---")
    st.subheader("Live Monitoring")
    
    if st.session_state.get('status') == 'RUNNING':
        # Simple Metrics: Strat / Profit / DD / DailyDD / WR / Trades
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Strategy", "595", "#")
        m2.metric("Profit", "+12.5%", "1,250$")
        m3.metric("Max DD", "-5.2%", "")
        m4.metric("Daily DD", "-1.1%", "")
        m5.metric("Winrate", "65%", "")
        m6.metric("Trades", "24", "")
        
        st.progress(45)
        st.write(f"Processing Batch: {timeframes}")
    else:
        st.write("Waiting for start...")

# --- Footer ---
st.markdown("---")
st.caption(f"Zenatus Backtester v2.0 | Dockerized | Connected to {BASE_PATH}")
