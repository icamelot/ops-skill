"""Threshold configuration loader."""

import os
from pathlib import Path
import yaml


class ThresholdConfig:
    """Loads and provides access to monitoring threshold configuration."""

    def __init__(self, config_path: str):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Threshold config not found: {config_path}")
        with open(config_path) as f:
            self._data = yaml.safe_load(f)

    @property
    def defaults(self) -> dict:
        return self._data.get("defaults", {})

    @property
    def check_interval(self) -> int:
        return self._data.get("check_interval_seconds", 300)

    @property
    def services(self) -> list[str]:
        return self._data.get("services", [])

    def get_servers(self) -> list[str]:
        """Return list of server identifiers."""
        return list(self._data.get("servers", {}).keys())

    def get_hostname(self, server_id: str) -> str:
        """Return the hostname/IP for a server identifier."""
        server = self._data.get("servers", {}).get(server_id, {})
        return server.get("hostname", server_id)

    def get_thresholds(self, server_id: str) -> dict:
        """Return merged thresholds for a server (server overrides merged onto defaults)."""
        merged = dict(self.defaults)
        server = self._data.get("servers", {}).get(server_id, {})
        merged.update(server)
        return merged
