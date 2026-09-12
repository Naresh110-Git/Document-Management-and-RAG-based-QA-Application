from __future__ import annotations

import asyncio
from collections import defaultdict
from time import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import error_payload


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        client = request.client.host if request.client else "anonymous"
        now = time()

        async with self._lock:
            window = self._buckets[client]
            window[:] = [timestamp for timestamp in window if timestamp + self.window_seconds > now]
            if len(window) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content=error_payload(code="rate_limit_exceeded", message="Rate limit exceeded"),
                )
            window.append(now)

        response = await call_next(request)
        return response
