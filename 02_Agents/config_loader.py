# -*- coding: utf-8 -*-
import os
import yaml
from pathlib import Path

class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # Default config path relative to this file
        base_dir = Path(__file__).parent.parent
        config_path = base_dir / "config" / "config.yaml"
        
        # Override with env var if present
        env_path = os.environ.get("ZENATUS_CONFIG_PATH")
        if env_path:
            config_path = Path(env_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)
            
        # Ensure paths are Path objects
        self._resolve_paths()

    def _resolve_paths(self):
        paths = self._config.get("paths", {})
        for key, value in paths.items():
            paths[key] = Path(value)

    def get(self, section, key=None, default=None):
        if not self._config:
            self._load_config()
        
        sec_data = self._config.get(section, {})
        if key is None:
            return sec_data
        return sec_data.get(key, default)

    @property
    def paths(self):
        return self._config.get("paths", {})

# Global instance
config = ConfigLoader()
