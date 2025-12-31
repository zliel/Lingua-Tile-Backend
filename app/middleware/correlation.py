from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.context import set_request_id, generate_request_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        set_request_id(request_id)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response
