"""Tests for middleware and monitoring endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.metrics import metrics_store


def test_monitoring_metrics_endpoint() -> None:
    client = TestClient(create_app())
    metrics_store.record_latency(12.5)

    response = client.get("/api/v1/monitoring/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "document_count" in data
    assert "average_request_latency_ms" in data
    assert data["service"] == "Document Management RAG API"


def test_monitoring_audit_log_count_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/monitoring/audit-log-count")
    assert response.status_code == 200
    assert "count" in response.json()


def test_rate_limit_middleware_blocks_after_threshold() -> None:
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)

    @test_app.get("/ping")
    def ping():
        return {"ping": "pong"}

    client = TestClient(test_app)

    # First two requests succeed
    r1 = client.get("/ping")
    assert r1.status_code == 200

    r2 = client.get("/ping")
    assert r2.status_code == 200

    # Third request is rate limited to 429
    r3 = client.get("/ping")
    assert r3.status_code == 429
    data = r3.json()
    assert "error" in data
    assert data["error"]["code"] == "rate_limit_exceeded"
