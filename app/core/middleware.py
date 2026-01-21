import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.errors import APIError

EXEMPT_PATH_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")

app = FastAPI(title="Throttle", version="0.1.0")
app.include_router(router)


def is_exempt_path(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PATH_PREFIXES)


@app.middleware("http")
async def throttle_middleware(request: Request, call_next):
    """
    ONE middleware that:
    1) assigns request_id
    2) enforces API key policy
    3) returns standardized errors for APIError
    4) guarantees X-Request-Id on every response
    """
    # 1) request id (always set first)
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id

    try:
        # 2) auth (skip for exempt paths)
        if not is_exempt_path(request.url.path) and settings.throttle_require_api_key:
            api_key = request.headers.get("x-api-key")
            if not api_key:
                raise APIError(
                    status_code=401,
                    code="AUTH_MISSING",
                    message="API key required. Provide it via the x-api-key header.",
                )
            if api_key not in settings.api_key_set:
                raise APIError(
                    status_code=403,
                    code="AUTH_INVALID",
                    message="Invalid API key.",
                )
            request.state.api_key = api_key

        # 3) continue to route handler
        response = await call_next(request)

    except APIError as exc:
        # Convert controlled errors into consistent JSON response
        payload = exc.to_dict(request_id=request_id,
                              path=str(request.url.path))
        response = JSONResponse(status_code=exc.status_code, content=payload)

    except Exception:
        # Convert unexpected errors into consistent JSON response
        payload = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error.",
                "details": {},
                "request_id": request_id,
                "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "path": str(request.url.path),
            }
        }
        response = JSONResponse(status_code=500, content=payload)

    # 4) always include request id header
    response.headers["X-Request-Id"] = request_id
    return response
