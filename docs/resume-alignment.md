# Resume Alignment

This document maps each resume bullet for Throttle to concrete code, demo, and interview evidence.

---

## Resume Bullets

```
Throttle — Redis-Backed Rate-Limiting API Gateway | Python, FastAPI, Redis, Docker, HTTP

- Built a Redis-backed API gateway enforcing per-API-key rate limits with
  standardized HTTP 429 responses + headers

- Implemented middleware-based auth and throttling to enforce consistent
  rate-limit policies across all endpoints

- Delivered a Dockerized service with a real-time dashboard for throughput,
  rate-limit events, and error monitoring
```

---

## Bullet 1 — Redis-backed per-API-key rate limits + HTTP 429 + headers

**Status: Fully supported**

### Code proof

| File | What it does |
|---|---|
| `app/core/rate_limit.py` | `check_rate_limit()` — INCR on `rl:<api_key>:<window_id>`, EXPIRE on first request. Returns `RateLimitResult` with `allowed`, `remaining`, `reset_epoch_seconds`, `retry_after_seconds`. |
| `app/main.py` | Middleware calls `check_rate_limit()`, raises `APIError(429)` when over limit, appends `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` headers to every response. |
| `app/core/redis_client.py` | Creates the Redis connection from `THROTTLE_REDIS_URL`. |

### Demo proof

```bash
for i in 1 2 3 4 5; do
  curl -si -H "x-api-key: dev_key_123" http://localhost:8000/api/v1/echo | grep -E "HTTP|X-RateLimit|Retry-After"
done
```

Expected: first 3 responses show `HTTP/1.1 200`, last 2 show `HTTP/1.1 429` with `Retry-After` and `X-RateLimit-*` headers.

### Interview proof

- Redis key design: `rl:<api_key>:<window_id>` where `window_id = unix_ts // window_seconds`
- INCR is atomic; EXPIRE is set only on count == 1 (first request in the window) to avoid resetting the timer mid-window
- `X-RateLimit-Remaining` = max(0, limit - count) so it never goes negative
- Trade-off of fixed window: a client can use 2× the limit across a boundary. Sliding window solves this at the cost of more Redis ops (ZRANGEBYSCORE + ZADD vs single INCR)

---

## Bullet 2 — Middleware-based auth and throttling across all endpoints

**Status: Fully supported**

### Code proof

| File | What it does |
|---|---|
| `app/main.py` | Single `@app.middleware("http")` function (`throttle_middleware`) handles: request ID assignment, x-api-key validation, Redis rate limiting, metrics recording, and header injection — in that order, for every request. |
| `app/core/errors.py` | `APIError` dataclass with `to_dict()` produces a consistent JSON error envelope regardless of where the error originates. |
| `app/core/config.py` | `EXEMPT_PATHS` and `NO_RATE_LIMIT_PATHS` are declared at the top of `main.py` — explicit and easy to trace in a walk-through. |

### Demo proof

```bash
# No key -> 401
curl -i http://localhost:8000/api/v1/echo

# Wrong key -> 403
curl -i -H "x-api-key: bad_key" http://localhost:8000/api/v1/echo

# Valid key -> 200 with rate-limit headers
curl -i -H "x-api-key: dev_key_123" http://localhost:8000/api/v1/echo

# Health check bypasses auth entirely
curl -i http://localhost:8000/health
```

### Interview proof

- One middleware = one place to change auth or rate-limit policy. No route can accidentally skip it.
- Exempt paths (health, docs, dashboard) are a named constant at the top of `main.py` — easy to see at a glance what is and isn't protected.
- Admin endpoints require auth but are excluded from rate limiting — operators need to monitor even while a key is throttled.

---

## Bullet 3 — Dockerized service with real-time dashboard

**Status: Fully supported**

### Code proof

| File | What it does |
|---|---|
| `Dockerfile` | Builds the FastAPI app on `python:3.11-slim`. Copies `requirements.txt` and `app/`, exposes port 8000, runs Uvicorn. |
| `docker-compose.yml` | Defines `redis` (Redis 7 Alpine) and `api` (built from Dockerfile) services. `api` depends on `redis` and uses `redis://redis:6379/0` as its Redis URL. |
| `app/api/dashboard.py` | Serves the dashboard HTML at `/dashboard`. |
| `app/static/dashboard.js` | Polls `/admin/metrics` and `/admin/events` every 2 seconds. Renders KPI cards, per-key breakdowns, and rate-limit event table. |
| `app/core/metrics.py` | Thread-safe counters: total, allowed, blocked, auth-missing, auth-invalid, per-key request and block counts. |
| `app/core/events.py` | Thread-safe rolling buffer (last 200 events) of 429 occurrences with timestamp, path, masked key, retry-after, and reset time. |

### Demo proof

```bash
cd api
docker compose up --build
# Open http://localhost:8000/dashboard
# Enter dev_key_123 in the API key input and click Save
# Run the rate limit loop — watch blocked count increment and events table update
```

### Interview proof

- "Dockerized" means `docker compose up --build` starts the full stack — Redis and the API — with no other setup.
- The dashboard is intentionally public (no auth) so you can open it during a demo without needing to configure anything. The data endpoints (`/admin/*`) still require a key.
- Metrics are in-memory: trade-off is simplicity vs durability. A production system would push to Redis or Prometheus.

---

## What Is Not Claimed (Honest Scope)

- No sliding window or token bucket (fixed window only)
- No per-endpoint rate limits (same limit applies to all protected routes for a given key)
- No Redis-backed metrics persistence (in-memory only)
- No admin-only vs user-only API keys
- No Prometheus / OpenTelemetry integration
- No TLS / production hardening
