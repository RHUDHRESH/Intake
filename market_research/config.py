from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    """Loads and caches configuration for the market research agent."""

    def __init__(
        self,
        path: Path,
        *,
        auto_reload: bool = True,
        reload_interval: float = 5.0,
    ) -> None:
        self._path = path
        self._auto_reload = auto_reload
        self._reload_interval = reload_interval
        self._lock = threading.RLock()
        self._last_loaded: float = 0.0
        self._last_mtime: float = 0.0
        self._config: Dict[str, Any] = {}

    def get(self) -> Dict[str, Any]:
        with self._lock:
            if self._should_reload():
                self._config = self._load()
                self._last_loaded = time.time()
            return dict(self._config)

    def get_site(self, site_key: str) -> Dict[str, Any]:
        config = self.get()
        sites = config.get("sites", {})
        return dict(sites.get(site_key, {}))

    def _should_reload(self) -> bool:
        if not self._config:
            return True
        if not self._auto_reload:
            return False
        if time.time() - self._last_loaded < self._reload_interval:
            return False
        try:
            mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            return False
        if mtime > self._last_mtime:
            self._last_mtime = mtime
            return True
        return False

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {}
        text = self._path.read_text(encoding="utf-8")
        if self._path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(text) or {}
        if self._path.suffix.lower() == ".json":
            return json.loads(text)
        raise ValueError(f"Unsupported config file extension: {self._path.suffix}")


__all__ = ["ConfigManager"]
