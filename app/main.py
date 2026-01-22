import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.errors import APIError
from app.core.redis_client import get_redis_client
from app.core.rate_limit import check_rate_limit

EXEMPT_PATH_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")

app = FastAPI(title="Throttle", version="0.2.0")
app.include_router(router)

redis_client = get_redis_client()


def is_exempt_path(path: str) -> bool:
    """
    Some paths should remain public:
    - health checks
    - API docs
    - openapi schema
    """
    return any(path.startswith(p) for p in EXEMPT_PATH_PREFIXES)


@app.middleware("http")
async def throttle_middleware(request: Request, call_next):
    """
    Throttle middleware (Day 2):

    1) assigns request_id (for tracing)
    2) enforces API key authentication
    3) applies Redis-backed fixed-window rate limiting per API key
    4) returns standardized errors for APIError + unexpected errors
    5) guarantees headers (X-Request-Id, X-RateLimit-*) on every response
    """
    # -------------------------
    # 1) Request ID
    # -------------------------
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id

    # We'll store rate-limit info on request.state so we can add headers later
    request.state.rate_limit = None

    try:
        # -------------------------
        # 2) Auth (skip exempt paths)
        # -------------------------
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

            # Save the key so routes/metrics can reference it
            request.state.api_key = api_key

            # -------------------------
            # 3) Rate limit (fixed window using Redis)
            # ------------------------

            rl = check_rate_limit(
                r=redis_client,
                api_key=api_key,
                limit=settings.throttle_rate_limit,
                window_seconds=settings.throttle_window_seconds,
            )

            # Save the rate limit result for headers (even on errors)
            request.state.rate_limit = rl

            if not rl.allowed:
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

        # -------------------------
        # 4) Continue to route handler
        # -------------------------
        response = await call_next(request)

    except APIError as exc:
        # Controlled errors: return standardized JSON envelope
        payload = exc.to_dict(request_id=request_id,
                              path=str(request.url.path))
        response = JSONResponse(status_code=exc.status_code, content=payload)

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print("\n--- UNHANDLED EXCEPTION ---")
        print(tb)
        print("--- END EXCEPTION ---\n")

        # In dev, include the exception message so you can diagnose faster.
        details = {}
        if settings.throttle_env == "dev":
            details = {"exception": repr(exc)}

        payload = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error.",
                "details": details,
                "request_id": request_id,
                "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "path": str(request.url.path),
            }
        }
        response = JSONResponse(status_code=500, content=payload)

    # -------------------------
    # 5) Always add headers
    # -------------------------
    response.headers["X-Request-Id"] = request_id

    # Rate limit headers only make sense on routes we rate-limit (protected routes)
    rl = getattr(request.state, "rate_limit", None)
    if rl is not None:
        response.headers["X-RateLimit-Limit"] = str(rl.limit)
        response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
        response.headers["X-RateLimit-Reset"] = str(rl.reset_epoch_seconds)

        if rl.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(rl.retry_after_seconds)

    return response
