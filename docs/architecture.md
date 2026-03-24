# Architecture

## Request Flow

```
Client
  |
  | HTTP request (x-api-key header)
  v
throttle_middleware  [app/main.py]
  |
  +-- 1. Assign request ID (X-Request-Id header or generate UUID)
  |
  +-- 2. Is path exempt? (health, docs, dashboard, static)
  |        YES -> skip auth + rate limit, go to route handler
  |        NO  -> continue
  |
  +-- 3. Auth: read x-api-key header
  |        missing  -> 401 AUTH_MISSING
  |        not in THROTTLE_API_KEYS -> 403 AUTH_INVALID
  |        valid    -> continue
  |
  +-- 4. Is path rate-limit exempt? (/admin/*)
  |        YES -> record allowed metric, go to route handler
  |        NO  -> continue
  |
  +-- 5. Rate limit check  [app/core/rate_limit.py]
  |        INCR rl:<api_key>:<window_id>  [Redis]
  |        EXPIRE window_seconds          [Redis, on first request only]
  |        count > limit -> record blocked metric + event
  |                      -> 429 RATE_LIMITED
  |        count <= limit -> record allowed metric, go to route handler
  |
  +-- 6. Route handler executes
  |
  +-- 7. Append headers to response:
           X-Request-Id
           X-RateLimit-Limit       (on rate-limited routes)
           X-RateLimit-Remaining   (on rate-limited routes)
           X-RateLimit-Reset       (on rate-limited routes)
           Retry-After             (only on 429 responses)
```

## Component Map

```
app/
  main.py
    - FastAPI app instance
    - throttle_middleware (single @app.middleware("http"))
    - EXEMPT_PATHS / NO_RATE_LIMIT_PATHS constants

  core/
    config.py       - Pydantic Settings (reads .env)
    rate_limit.py   - check_rate_limit() -> RateLimitResult
    redis_client.py - Redis.from_url() (one client, shared connection pool)
    metrics.py      - MetricsStore (thread-safe in-memory counters)
    events.py       - EventStore (thread-safe rolling buffer, max 200 events)
    errors.py       - APIError + to_dict() -> standardized JSON envelope

  api/
    routes.py       - APIRouter: /health, /api/v1/echo, includes admin + dashboard
    admin.py        - GET /admin/metrics, GET /admin/events
    dashboard.py    - GET /dashboard (HTML)

  static/
    dashboard.js    - Polls /admin/metrics + /admin/events every 2s, renders UI
```

## Data Flows

### Rate limit counter (Redis)

```
Key:   rl:<api_key>:<window_id>
       api_key    = raw API key string (e.g. "dev_key_123")
       window_id  = unix_timestamp // window_seconds

Value: integer counter (INCR)
TTL:   window_seconds (set via EXPIRE on first INCR only)
```

Example with `THROTTLE_WINDOW_SECONDS=60`:
- Unix time 1700000045 → window_id = 28333334
- Key: `rl:dev_key_123:28333334`
- TTL: 60 seconds from first request in window

### Metrics (in-memory)

```
MetricsStore (singleton, process lifetime)
  _total_requests     int
  _allowed_requests   int
  _blocked_requests   int
  _auth_missing       int
  _auth_invalid       int
  _requests_by_key    dict[masked_key -> int]
  _blocked_by_key     dict[masked_key -> int]
```

All mutations use a threading.Lock. Keys are masked (first 3 chars + `***`) before storage.

### Events (in-memory)

```
EventStore (singleton, max 200 events)
  _events  list[RateLimitEvent]
    .timestamp_epoch
    .request_id
    .path
    .api_key_masked
    .status_code  (always 429)
    .details      { limit, remaining, reset, retry_after, count }
```

Rolling buffer: when len > max_events, oldest entries are dropped.

## Design Decisions

**Single middleware vs per-route dependencies**  
All gateway policy lives in one place. Every request goes through the same code path — nothing can accidentally bypass auth or rate limiting. The trade-off is that exempt paths (health, docs, dashboard) must be explicitly listed.

**Fixed-window rate limiting**  
One Redis operation per request (INCR). Simple, predictable, easy to explain. Known limitation: allows bursts at window boundaries. Token bucket or sliding window would prevent this at the cost of more Redis complexity.

**In-memory metrics and events**  
No external dependencies for observability. Resets on process restart. Acceptable for this scope; production would use Redis counters or a Prometheus exporter.

**Shared Redis client**  
`get_redis_client()` is called once at startup and the client is shared for the process lifetime. The `redis-py` client maintains a connection pool internally — no need to manage connections per request.
