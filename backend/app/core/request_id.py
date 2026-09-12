from __future__ import annotations

import contextvars
import uuid

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="unknown")


def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)
