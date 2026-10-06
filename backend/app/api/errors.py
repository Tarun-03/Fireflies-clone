import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.core.errors import DomainError

logger = logging.getLogger("workspace")


def response(
    request: Request,
    status: int,
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "field_errors": fields or [],
                "request_id": request_id,
            }
        },
        status_code=status,
        headers={"Cache-Control": "no-store", "X-Request-ID": request_id},
    )


def install_errors(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain(request: Request, exc: DomainError) -> JSONResponse:
        return response(request, exc.status, exc.code, exc.message, exc.field_errors)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": "Check this value."}
            for error in exc.errors()[:20]
        ]
        return response(request, 422, "invalid_input", "Some values need your attention.", fields)

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        return response(
            request,
            409,
            "constraint_conflict",
            "This change conflicts with existing content. Review the values and try again.",
        )

    @app.exception_handler(OperationalError)
    async def unavailable(request: Request, exc: OperationalError) -> JSONResponse:
        return response(
            request,
            503,
            "unavailable",
            "The workspace is temporarily unavailable. Try again shortly.",
        )

    @app.exception_handler(HTTPException)
    async def http(request: Request, exc: HTTPException) -> JSONResponse:
        return response(
            request, exc.status_code, "request_rejected", "This request could not be completed."
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "request_failed request_id=%s error_type=%s",
            getattr(request.state, "request_id", ""),
            type(exc).__name__,
        )
        return response(request, 500, "internal_error", "Something went wrong. Please try again.")
