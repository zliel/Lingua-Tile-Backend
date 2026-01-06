import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    """
    Get the current request ID from context.
    Returns 'unknown' if not set (e.g. outside of request context).
    """
    return request_id_ctx.get() or "unknown"


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.
    """
    request_id_ctx.set(request_id)


def generate_request_id() -> str:
    """
    Generate a new unique request ID.
    """
    return str(uuid.uuid4())
