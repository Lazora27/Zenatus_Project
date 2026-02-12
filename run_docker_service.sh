#!/usr/bin/env bash
set -e

# Change to project root
cd /opt

# Ensure docker daemon is running
# sudo systemctl start docker

# Pull latest changes (if any) or rebuild
# docker-compose pull backtester

# Start services in detached mode
# Force recreate to ensure config changes are picked up
/usr/bin/docker-compose up -d --build --remove-orphans

# Follow logs of backtester to keep systemd service active (optional, but good for journalctl)
# Or just exit if Type=oneshot/forking
/usr/bin/docker-compose logs -f backtester
