from __future__ import annotations

from time import perf_counter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.metrics import metrics_store


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        start = perf_counter()
        response = await call_next(request)
        latency_ms = (perf_counter() - start) * 1000
        metrics_store.record_latency(latency_ms)
        return response
