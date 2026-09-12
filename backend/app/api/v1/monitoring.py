from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.models.audit import AuditLog
from app.models.document import Document
from app.services.metrics import metrics_store

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/metrics")
async def metrics() -> JSONResponse:
    settings = get_settings()
    doc_count = 0
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(Document.id)))
            doc_count = result.scalar() or 0
    except Exception:
        doc_count = 0

    avg_latency = metrics_store.get_average_latency()
    metrics_data = {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(metrics_store.get_uptime(), 2),
        "document_count": doc_count,
        "average_request_latency_ms": round(avg_latency, 2) if avg_latency is not None else None,
    }
    return JSONResponse(content=metrics_data)


@router.get("/audit-log-count")
async def audit_log_count() -> JSONResponse:
    count = 0
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(AuditLog.id)))
            count = result.scalar() or 0
    except Exception:
        count = 0
    return JSONResponse(content={"count": count})
