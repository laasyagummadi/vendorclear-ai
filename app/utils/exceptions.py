# ─────────────────────────────────────────────────────────────
#  app/utils/exceptions.py  —  Custom exceptions + handlers
# ─────────────────────────────────────────────────────────────
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger


# ── Custom exception classes ──────────────────────────────────
class VendorClearException(Exception):
    """Base exception for VendorClear AI."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(VendorClearException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class ConflictError(VendorClearException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class AuthenticationError(VendorClearException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class AuthorizationError(VendorClearException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class ValidationError(VendorClearException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


# ── Handler registration ──────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(VendorClearException)
    async def vendorclear_exception_handler(
        request: Request, exc: VendorClearException
    ) -> JSONResponse:
        logger.warning(f"{exc.__class__.__name__}: {exc.message} — {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        logger.warning(f"Validation error on {request.url}: {details}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Validation failed",
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Internal server error"},
        )
