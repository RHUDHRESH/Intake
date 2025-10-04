"""Helper utilities for configuration retrieval and storage."""
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict

DOTENV_FILE = Path(os.getenv("DOTENV_FILE", ".env"))
CONFIG_STORE_FILE = Path(os.getenv("CONFIG_STORE_FILE", "config_store.json"))

try:  # Optional dependency
    from google.cloud import secretmanager
except ImportError:  # pragma: no cover - optional
    secretmanager = None


def _read_dotenv_value(key: str) -> Dict[str, Any]:
    if not DOTENV_FILE.exists():
        return {"error": f"dotenv file not found: {DOTENV_FILE}"}

    with DOTENV_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith(f"{key}="):
                value = stripped.split("=", 1)[1]
                return {"key": key, "value": value}
    return {"key": key, "value": None}


def _read_store_value(key: str) -> Dict[str, Any]:
    if not CONFIG_STORE_FILE.exists():
        return {"error": f"config store not found: {CONFIG_STORE_FILE}"}
    with CONFIG_STORE_FILE.open("r", encoding="utf-8") as handle:
        try:
            store = json.load(handle)
        except json.JSONDecodeError as exc:
            return {"error": f"config store is not valid JSON: {exc}"}
    return {"key": key, "value": store.get(key)}


def _write_store_value(key: str, value: Any) -> Dict[str, Any]:
    store = {}
    if CONFIG_STORE_FILE.exists():
        with CONFIG_STORE_FILE.open("r", encoding="utf-8") as handle:
            try:
                store = json.load(handle)
            except json.JSONDecodeError:
                store = {}
    store[key] = value
    CONFIG_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_STORE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=2)
    return {"key": key, "value": value, "status": "set"}


def _get_config_sync(key: str, source: str) -> Dict[str, Any]:
    normalized = (source or "env").lower()
    if normalized == "env":
        return {"key": key, "value": os.getenv(key)}
    if normalized == "dotenv":
        return _read_dotenv_value(key)
    if normalized == "store":
        return _read_store_value(key)
    return {"error": f"unknown config source: {source}"}


def _set_config_sync(key: str, value: Any, source: str) -> Dict[str, Any]:
    normalized = (source or "store").lower()
    if normalized == "store":
        return _write_store_value(key, value)
    return {"error": f"setting source '{source}' is not supported"}


def _fetch_secret_sync(key: str) -> Dict[str, Any]:
    if secretmanager is None:
        return {"error": "google-cloud-secret-manager is not installed"}
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        return {"error": "GOOGLE_CLOUD_PROJECT environment variable is not set"}

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{key}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
    except Exception as exc:  # pragma: no cover - API specific errors
        return {"error": str(exc)}
    secret_value = response.payload.data.decode("utf-8")
    return {"key": key, "value": secret_value}


async def get_config(key: str, source: str = "env") -> Dict[str, Any]:
    return await asyncio.to_thread(_get_config_sync, key, source)


async def set_config(key: str, value: Any, source: str = "store") -> Dict[str, Any]:
    return await asyncio.to_thread(_set_config_sync, key, value, source)


async def fetch_secret(key: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_fetch_secret_sync, key)
