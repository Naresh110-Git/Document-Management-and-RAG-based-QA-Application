"""Global exception handlers."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error converted into a structured JSON response."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "application_error"
    message = "Application error"
    headers: dict[str, str] | None = None

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        self.headers = headers or self.headers
        super().__init__(self.message)


class AuthenticationError(AppError):
    """Raised when a request lacks valid authentication."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_failed"
    message = "Authentication failed"
    headers = {"WWW-Authenticate": "Bearer"}


class AuthorizationError(AppError):
    """Raised when an authenticated user lacks required permissions."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "authorization_failed"
    message = "Insufficient permissions"


class ConflictError(AppError):
    """Raised when a resource conflicts with an existing resource."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Resource conflict"


def error_payload(code: str, message: str, details: object | None = None) -> dict[str, object]:
    """Build a consistent API error response."""
    payload: dict[str, object] = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details is not None:
        payload["error"]["details"] = details  # type: ignore[index]

    return payload


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code=exc.code, message=exc.message, details=exc.details),
            headers=exc.headers,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code="http_error",
                message=str(exc.detail),
            ),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload(
                code="validation_error",
                message="Request validation failed",
                details=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload(
                code="internal_server_error",
                message="An unexpected error occurred",
            ),
        )
