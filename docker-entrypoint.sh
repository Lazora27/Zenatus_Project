#!/bin/bash
set -e

echo "[INIT] Zenatus Backtester Container Starting..."

# Ensure config exists, if not, copy default
if [ ! -f /app/Zenatus_Backtester/config/config.yaml ]; then
    echo "[INIT] Config not found, copying example..."
    mkdir -p /app/Zenatus_Backtester/config
    cp /app/Zenatus_Backtester/config/config.yaml.example /app/Zenatus_Backtester/config/config.yaml || echo "No example config found"
fi

# Ensure log directories exist (they are mounted volumes, might be empty)
mkdir -p /app/Zenatus_Dokumentation/LOG/1h
mkdir -p /app/Zenatus_Dokumentation/Listing
mkdir -p /app/Zenatus_Dokumentation/Dokumentation/Fixed_Exit

# Fix permissions if needed (optional, depends on host user)
# chown -R 1000:1000 /app/Zenatus_Dokumentation

echo "[INIT] Environment check complete."
echo "[INIT] Executing command: $@"

exec "$@"
