"""Audit-log repository."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditLogRepository:
    """Persistence operations for audit log records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        action: str,
        entity_type: str,
        actor_user_id: UUID | None = None,
        entity_id: UUID | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry without committing the transaction."""
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log
