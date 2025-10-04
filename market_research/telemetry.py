from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional metrics
    from prometheus_client import Counter, Gauge, Histogram
except Exception:  # pragma: no cover
    class _Noop:
        def __init__(self, *_, **__):
            pass

        def labels(self, *_, **__):
            return self

        def inc(self, *_):
            return None

        def dec(self, *_):
            return None

        def time(self):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, *exc):
                    return False

            return _Ctx()

        def observe(self, *_):
            return None

    Counter = Gauge = Histogram = _Noop  # type: ignore

try:  # pragma: no cover - optional tracing
    from opentelemetry import trace
    from opentelemetry.trace import Span
except Exception:  # pragma: no cover
    trace = None  # type: ignore
    Span = None  # type: ignore


logger = logging.getLogger("market_research")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(getattr(logging, os.getenv("MARKET_RESEARCH_LOG_LEVEL", "INFO").upper(), logging.INFO))

REQUEST_COUNTER = Counter("market_fetch_requests", "Total fetch attempts", ["site"])
REQUEST_FAILURE = Counter("market_fetch_failures", "Fetch failures", ["site"])
REQUEST_LATENCY = Histogram("market_fetch_latency_seconds", "Fetch latency", ["site"])
PIPELINE_GAUGE = Gauge("market_pipeline_inflight", "Number of inflight research jobs")


def emit_log(message: str, *, extra: Optional[Dict[str, Any]] = None, level: int = logging.INFO) -> None:
    payload = {"message": message, **(extra or {})}
    logger.log(level, json.dumps(payload))


@contextmanager
def traced_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    if trace is None:  # pragma: no cover
        yield None
        return
    tracer = trace.get_tracer("market_research")
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


__all__ = [
    "PIPELINE_GAUGE",
    "REQUEST_COUNTER",
    "REQUEST_FAILURE",
    "REQUEST_LATENCY",
    "emit_log",
    "traced_span",
]
