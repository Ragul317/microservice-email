"""Uniform error responses: {"success": false, "message": ..., "errors": [...]}."""
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def error_response(status_code: int, message: str, errors: list | None = None) -> JSONResponse:
    content = {"success": False, "message": message}
    if errors is not None:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        if err.get("type") == "json_invalid":
            field = "body"
        else:
            field = ".".join(str(part) for part in err["loc"] if part != "body") or "body"
        message = str(err["msg"]).removeprefix("Value error, ")
        errors.append({"field": field, "message": message})
    logger.info("Validation failed for fields: %s", ", ".join(e["field"] for e in errors))
    return error_response(422, "Validation failed", errors)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "Internal server error")
