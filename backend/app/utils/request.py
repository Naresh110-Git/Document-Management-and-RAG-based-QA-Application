"""Request metadata helpers."""

from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class RequestMetadata:
    """Small audit-safe subset of request metadata."""

    ip_address: str | None
    user_agent: str | None


def request_metadata_from(request: Request) -> RequestMetadata:
    """Extract client metadata for audit logging."""
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = forwarded_for.split(",", maxsplit=1)[0].strip() if forwarded_for else None

    if not ip_address and request.client:
        ip_address = request.client.host

    return RequestMetadata(
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )
