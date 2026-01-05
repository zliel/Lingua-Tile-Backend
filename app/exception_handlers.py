import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(_: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    Returns a 500 Internal Server Error with a standardized JSON structure.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": 500,
            "message": "Internal Server Error",
            "details": str(exc)
            if not str(exc) == ""
            else "An unexpected error occurred.",
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Override default HTTP exception handler to return consistent JSON.
    """
    logger.error(f"{request}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "message": exc.detail,
            "details": None,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Override default validation error handler.
    """
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logger.error(f"{request}: {exc_str}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status_code": 422, "message": "Validation Error", "details": exc_str},
    )


def add_exception_handlers(app: FastAPI):
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
