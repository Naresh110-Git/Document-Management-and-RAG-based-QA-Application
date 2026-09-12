from __future__ import annotations

import time
from collections import deque
from typing import Deque


class MetricsStore:
    def __init__(self, max_samples: int = 1000) -> None:
        self.request_latencies: Deque[float] = deque(maxlen=max_samples)
        self.start_time = time.time()

    def record_latency(self, latency_ms: float) -> None:
        self.request_latencies.append(latency_ms)

    def get_average_latency(self) -> float | None:
        if not self.request_latencies:
            return None
        return sum(self.request_latencies) / len(self.request_latencies)

    def get_uptime(self) -> float:
        return time.time() - self.start_time


metrics_store = MetricsStore()
