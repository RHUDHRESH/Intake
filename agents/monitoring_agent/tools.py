"""Helper functions for monitoring agent logging and metrics."""
import asyncio
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

LOG_FILE = Path(os.getenv("LOG_FILE", "system_log.jsonl"))
METRICS_FILE = Path(os.getenv("METRICS_FILE", "metrics_log.jsonl"))


def _append_jsonl(path: Path, record: Mapping[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"status": "written", "file": str(path)}


def _log_event_sync(event_type: str, event: str, details: Mapping[str, Any]) -> Dict[str, Any]:
    record = {
        "type": event_type,
        "event": event,
        "details": dict(details),
        "timestamp": dt.datetime.utcnow().isoformat(),
    }
    _append_jsonl(LOG_FILE, record)
    return {"status": f"{event_type}_logged", "event": event}


def _track_metric_sync(metric: str, value: Any) -> Dict[str, Any]:
    record = {
        "metric": metric,
        "value": value,
        "timestamp": dt.datetime.utcnow().isoformat(),
    }
    _append_jsonl(METRICS_FILE, record)
    return {"status": "metric_tracked", "metric": metric, "value": value}


def _fetch_logs_sync(query: Mapping[str, Any]) -> Dict[str, Any]:
    path = LOG_FILE
    if not path.exists():
        return {"logs": []}

    results = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if _matches_query(record, query):
                results.append(record)
    return {"logs": results}


def _matches_query(record: Mapping[str, Any], query: Mapping[str, Any]) -> bool:
    for key, expected in query.items():
        if record.get(key) != expected:
            return False
    return True


async def log_event(event: str, details: Mapping[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(_log_event_sync, "event", event, details)


async def log_error(event: str, details: Mapping[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(_log_event_sync, "error", event, details)


async def track_metric(metric: str, value: Any) -> Dict[str, Any]:
    return await asyncio.to_thread(_track_metric_sync, metric, value)


async def fetch_logs(query: Mapping[str, Any]) -> Dict[str, Any]:
    query_mapping = dict(query) if isinstance(query, Mapping) else {}
    return await asyncio.to_thread(_fetch_logs_sync, query_mapping)
