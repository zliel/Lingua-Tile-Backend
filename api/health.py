from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint that verifies API and database connectivity.
    Returns 200 if healthy, 503 if database is unreachable.
    """
    result = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "unknown",
    }

    try:
        if hasattr(request.app.state, "mongo_client"):
            client = request.app.state.mongo_client
            await client.admin.command("ping")
            result["database"] = "connected"
        else:
            result["database"] = "not_configured"
            result["status"] = "degraded"
    except Exception as e:
        result["database"] = "disconnected"
        result["status"] = "unhealthy"
        result["error"] = str(e)
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content=result)

    return result
