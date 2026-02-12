# Zenatus Backtester - Deployment Guide

This guide explains how to deploy the Zenatus Backtester using Docker and Systemd.

## Prerequisites
- Docker Engine & Docker Compose
- Git
- Python 3.10+ (for local scripts if needed)

## Installation

1. **Clone Repository**
   ```bash
   git clone git@github.com:Lazora27/Zenatus_Project.git /opt/Zenatus_Backtester
   cd /opt/Zenatus_Backtester
   ```

2. **Configure Environment**
   - Copy example config: `cp config/config.yaml.example config/config.yaml`
   - Edit `config/config.yaml` to set your paths and preferences.
   - (Optional) Set up `.env` for Docker if needed.

3. **Start Services (Docker)**
   To run manually:
   ```bash
   docker-compose up -d --build
   ```
   Check logs:
   ```bash
   docker-compose logs -f backtester
   ```

4. **Enable Autostart (Systemd)**
   The systemd service `zenatus_backtest.service` manages the Docker container.
   ```bash
   sudo cp zenatus_backtest.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable zenatus_backtest.service
   sudo systemctl start zenatus_backtest.service
   ```

## Updates
To update the system with the latest code from GitHub:
1. Pull changes: `git pull`
2. Restart service: `sudo systemctl restart zenatus_backtest.service` (This triggers a rebuild/recreate of the container).

## Troubleshooting
- **Container keeps restarting:** Check logs with `docker logs zenatus_backtest_engine`.
- **Permission Denied:** Ensure the user running docker has access to `/opt/Zenatus_Backtester`.
- **Config changes not applied:** You must restart the container/service.

## CI/CD
A GitHub Action workflow is located in `.github/workflows/docker-build.yml`.
It builds the image on every push to `main` to verify integrity.
To enable DockerHub push, set `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets in GitHub.
