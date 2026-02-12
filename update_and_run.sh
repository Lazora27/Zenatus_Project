#!/bin/bash
echo ">>> Zenatus Local Build Script <<<"

# 1. Pull latest changes
echo "[1/4] Pulling updates from Git..."
git pull origin main

# 2. Rebuild Docker Image
echo "[2/4] Rebuilding Docker Image..."
sudo docker-compose up -d --build

# 3. Test Alert
echo "[3/4] Sending Test Alert..."
sudo docker exec zenatus_backtest_engine python /app/Zenatus_Backtester/02_Agents/alert_agent.py

# 4. Status
echo "[4/4] Checking Status..."
sudo docker ps | grep zenatus
echo "Done! Access GUI at http://<YOUR_IP>:8501"
