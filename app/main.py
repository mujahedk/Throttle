import traceback
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.core.errors import APIError
from app.core.redis_client import get_redis_client
from app.core.rate_limit import check_rate_limit
from app.core.metrics import metrics
from app.core.events import events

# Paths that bypass auth entirely (health, docs, dashboard UI)
EXEMPT_PATHS = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/dashboard",
    "/static",
)

# Paths that require auth but are not rate-limited (admin/observability)
NO_RATE_LIMIT_PATHS = ("/admin",)

app = FastAPI(title="Throttle", version="0.3.0")
app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

redis_client = get_redis_client()


def is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PATHS)


def is_rate_limit_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in NO_RATE_LIMIT_PATHS)


@app.middleware("http")
async def throttle_middleware(request: Request, call_next):
    """
    Single middleware that enforces all gateway policies in order:
      1. Assign a request ID for tracing
      2. Authenticate via x-api-key header
      3. Apply Redis fixed-window rate limiting per API key
      4. Record metrics and rate-limit events
      5. Attach X-RateLimit-* headers to every response
    """
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.rate_limit = None

    metrics.inc_total()

    try:
        if not is_exempt(request.url.path) and settings.throttle_require_api_key:
            api_key = request.headers.get("x-api-key")

            if not api_key:
                metrics.inc_auth_missing()
                raise APIError(
                    status_code=401,
                    code="AUTH_MISSING",
                    message="API key required. Provide it via the x-api-key header.",
                )

            if api_key not in settings.api_key_set:
                metrics.inc_auth_invalid()
                raise APIError(
                    status_code=403,
                    code="AUTH_INVALID",
                    message="Invalid API key.",
                )

            request.state.api_key = api_key

            if not is_rate_limit_exempt(request.url.path):
                rl = check_rate_limit(
                    r=redis_client,
                    api_key=api_key,
                    limit=settings.throttle_rate_limit,
                    window_seconds=settings.throttle_window_seconds,
                )
                request.state.rate_limit = rl

                if rl.allowed:
                    metrics.inc_allowed(api_key)
                else:
                    metrics.inc_blocked(api_key)
                    events.add_rate_limit_event(
                        request_id=request_id,
                        path=str(request.url.path),
                        api_key=api_key,
                        details={
                            "limit": rl.limit,
                            "remaining": rl.remaining,
                            "reset": rl.reset_epoch_seconds,
                            "retry_after": rl.retry_after_seconds,
                            "count": rl.current_count,
                        },
                    )
                    raise APIError(
                        status_code=429,
                        code="RATE_LIMITED",
                        message="Too many requests. Please retry later.",
                        details={
                            "limit": rl.limit,
                            "remaining": rl.remaining,
                            "reset": rl.reset_epoch_seconds,
                            "retry_after": rl.retry_after_seconds,
                            "count": rl.current_count,
                        },
                    )
            else:
                metrics.inc_allowed(api_key)

        response = await call_next(request)

    except APIError as exc:
        payload = exc.to_dict(request_id=request_id, path=str(request.url.path))
        response = JSONResponse(status_code=exc.status_code, content=payload)

    except Exception as exc:
        tb = traceback.format_exc()
        print(f"\n--- UNHANDLED EXCEPTION ---\n{tb}--- END EXCEPTION ---\n")

        details = {}
        if settings.throttle_env == "dev":
            details = {"exception": repr(exc)}

        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error.",
                    "details": details,
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "path": str(request.url.path),
                }
            },
        )

    response.headers["X-Request-Id"] = request_id

    rl = getattr(request.state, "rate_limit", None)
    if rl is not None:
        response.headers["X-RateLimit-Limit"] = str(rl.limit)
        response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
        response.headers["X-RateLimit-Reset"] = str(rl.reset_epoch_seconds)
        if rl.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(rl.retry_after_seconds)

    return response
