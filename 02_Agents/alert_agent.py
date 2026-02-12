# -*- coding: utf-8 -*-
import requests
import json
import os
import sys
from pathlib import Path

# Try import config/logger
try:
    from config_loader import config
    from logger_setup import logger
except ImportError:
    import logging
    logger = logging.getLogger("AlertAgent")
    # Fallback config
    class ConfigMock:
        def get(self, section, key, default=None): return default
    config = ConfigMock()

class AlertAgent:
    def __init__(self):
        self.discord_webhook = config.get("alerts", "discord_webhook_url")
        self.telegram_token = config.get("alerts", "telegram_bot_token")
        self.telegram_chat_id = config.get("alerts", "telegram_chat_id")
        self.enabled = config.get("alerts", "enabled", False)

    def send_discord(self, message, level="INFO"):
        if not self.discord_webhook:
            return False
            
        color = 0x00ff00 # Green
        if level == "ERROR": color = 0xff0000 # Red
        if level == "WARNING": color = 0xffff00 # Yellow
        
        payload = {
            "embeds": [{
                "title": f"Zenatus Alert: {level}",
                "description": message,
                "color": color,
                "footer": {"text": "Zenatus Backtester"}
            }]
        }
        
        try:
            resp = requests.post(self.discord_webhook, json=payload)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    def send_telegram(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            return False
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": f"[Zenatus] {message}",
            "parse_mode": "Markdown"
        }
        
        try:
            resp = requests.post(url, json=payload)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False

    def alert(self, message, level="INFO"):
        if not self.enabled:
            return
            
        # Send to all configured channels
        d_ok = self.send_discord(message, level)
        t_ok = self.send_telegram(message)
        
        if d_ok or t_ok:
            logger.info(f"Alert sent: {message}")
        else:
            logger.warning(f"Could not send alert (check config): {message}")

if __name__ == "__main__":
    # Test run
    agent = AlertAgent()
    if agent.enabled:
        agent.alert("Test Alert from Zenatus Backtester", "INFO")
    else:
        print("Alerts are disabled in config.yaml")
