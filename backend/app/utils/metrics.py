"""Prometheus metrics helpers for API monitoring."""

from __future__ import annotations

import importlib
from typing import Any


def _load_prometheus() -> tuple[Any, Any, Any]:
    try:
        module = importlib.import_module("prometheus_client")
    except Exception as exc:
        raise ImportError("prometheus_client is required for metrics endpoint") from exc
    return getattr(module, "Counter"), getattr(module, "Histogram"), getattr(module, "generate_latest")


try:
    Counter, Histogram, _generate_latest = _load_prometheus()
    HTTP_REQUESTS_TOTAL = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
    HTTP_REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "path"])
except Exception:
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION = None
    _generate_latest = None


def observe_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    if HTTP_REQUESTS_TOTAL is not None:
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
    if HTTP_REQUEST_DURATION is not None:
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration_seconds)


def render_metrics() -> bytes:
    if _generate_latest is None:
        return b""
    return _generate_latest()
