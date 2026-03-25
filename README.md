# Throttle

A Redis-backed API gateway that enforces per-API-key rate limits, returns standardized HTTP responses, and exposes a real-time dashboard for monitoring throughput and rate-limit events.

---

## Working API Key / Dashboard

![Working API Key / Dashboard](/demo-photos/throttle-working-api-key.png)

## Quick Start

Requires Docker Desktop. All commands run from the `api/` directory.

```bash
make start   # build + start Redis and API, wait until ready (~30s)
make seed    # fire pre-demo requests to populate the dashboard
```

Open **http://localhost:8000/dashboard** — the dashboard auto-authenticates and shows live data.

```bash
make demo    # run the rate-limit loop: 200 200 200 429 429
make reset   # flush Redis counters to run the demo again
make stop    # shut everything down
```

No `make` on your machine? Run the scripts directly:

```bash
bash scripts/start.sh
bash scripts/seed.sh
bash scripts/demo.sh
bash scripts/reset_redis.sh
docker compose down
```

See [`docs/demo-script.md`](docs/demo-script.md) for the full demo flow.

---

## Architecture

```
Client Request
     |
     v
throttle_middleware  (app/main.py)
     |
     +-- Assign request ID
     |
     +-- Auth: validate x-api-key header
     |         missing  -> 401 AUTH_MISSING
     |         invalid  -> 403 AUTH_INVALID
     |
     +-- Rate limit: Redis INCR + EXPIRE
     |         over limit -> 429 RATE_LIMITED + Retry-After / X-RateLimit-* headers
     |
     +-- Record metrics + events (in-memory)
     |
     v
Route handler -> response
     |
     v
X-RateLimit-Limit / X-RateLimit-Remaining / X-RateLimit-Reset headers appended
```

**Redis key design:** `rl:<api_key>:<window_id>` where `window_id = unix_timestamp // window_seconds`. Each key gets a TTL equal to the window duration.

**In-memory state:** metrics counters and the rate-limit event buffer live in the process. They reset on restart — intentional for this scope. A production system would use Redis or Prometheus.

---

## Project Structure

```
api/
  app/
    main.py            # FastAPI app + single HTTP middleware (auth + rate limiting)
    core/
      config.py        # Pydantic settings (reads from .env)
      rate_limit.py    # Fixed-window Redis counter logic
      redis_client.py  # Redis connection
      metrics.py       # Thread-safe in-memory counters
      events.py        # Thread-safe rolling event buffer
      errors.py        # APIError + JSON error envelope
    api/
      routes.py        # Router: health, echo, includes admin + dashboard
      admin.py         # GET /admin/metrics, GET /admin/events
      dashboard.py     # GET /dashboard (serves HTML)
    static/
      dashboard.js     # Dashboard polling + rendering logic
  scripts/
    demo.sh            # Run the rate-limit demo loop (one command)
    reset_redis.sh     # Flush Redis counters between demo runs
    ping_redis.py      # Verify Redis connectivity
    print_settings.py  # Print resolved config values
  docs/
    architecture.md    # Request flow, component map, data flow, design decisions
    demo-script.md     # Step-by-step demo guide (30s / 2min / 5min explanations)
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env.example
```

---

## Running the Project

### Option A — Docker (full stack)

Starts both Redis and the API in containers:

```bash
cd api
docker compose up --build
```

The API will be available at `http://localhost:8000`.

To stop:

```bash
docker compose down
```

### Option B — Local (Redis in Docker, API with Uvicorn)

```bash
# 1. Start Redis
cd api
docker compose up -d redis

# 2. Set up Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Copy env file
cp .env.example .env
# Edit .env to set your preferred rate limit

# 4. Run the API
uvicorn app.main:app --reload --port 8000
```

---

## Authentication

All non-health, non-dashboard endpoints require an API key:

```http
x-api-key: dev_key_123
```

Configured via `THROTTLE_API_KEYS` (comma-separated list in `.env`).

| Scenario    | Response                     |
| ----------- | ---------------------------- |
| Missing key | `401 AUTH_MISSING`           |
| Invalid key | `403 AUTH_INVALID`           |
| Valid key   | Proceeds to rate limit check |

---

## Rate Limiting

**Strategy:** fixed window per API key  
**Backend:** Redis  
**Mechanism:** `INCR` on `rl:<api_key>:<window_id>`, `EXPIRE` on first increment

With `THROTTLE_RATE_LIMIT=3` and `THROTTLE_WINDOW_SECONDS=60`:

```
Request 1  ->  200  (X-RateLimit-Remaining: 2)
Request 2  ->  200  (X-RateLimit-Remaining: 1)
Request 3  ->  200  (X-RateLimit-Remaining: 0)
Request 4  ->  429  (Retry-After: <seconds until window resets>)
```

**Response headers on every protected request:**

| Header                  | Meaning                                       |
| ----------------------- | --------------------------------------------- |
| `X-RateLimit-Limit`     | Max requests allowed per window               |
| `X-RateLimit-Remaining` | Requests left in current window               |
| `X-RateLimit-Reset`     | Unix timestamp when the window resets         |
| `Retry-After`           | Seconds to wait before retrying (only on 429) |

**Trade-off:** fixed window is simpler and uses one Redis operation per request. The downside is burst tolerance — a client can consume 2x the limit across a window boundary. Sliding window or token bucket would prevent this at the cost of more Redis operations.

---

## Endpoints

| Method | Path             | Auth | Rate Limited |
| ------ | ---------------- | ---- | ------------ |
| GET    | `/health`        | No   | No           |
| GET    | `/api/v1/echo`   | Yes  | Yes          |
| GET    | `/admin/metrics` | Yes  | No           |
| GET    | `/admin/events`  | Yes  | No           |
| GET    | `/dashboard`     | No   | No           |

Admin endpoints require a valid API key but are excluded from rate limiting so operators can observe the system even while a key is throttled.

---

## Dashboard

Open `http://localhost:8000/dashboard` in a browser.

Enter a valid API key in the input at the top right, then click Save. The dashboard auto-refreshes every 2 seconds and shows:

- Total / Allowed / Blocked / Auth-error counts
- Request and block counts broken down by API key (masked)
- Recent rate-limit events table with path, key, retry-after, reset time, and request count

## ![Invalid API Key](/demo-photos/throttle-invalid-api-key.png)

## Demo Commands

### Health check

```bash
curl http://localhost:8000/health
```

### Trigger rate limiting

Run the demo script (requires the server to be running):

```bash
bash scripts/demo.sh
```

Or manually:

```bash
for i in 1 2 3 4 5; do
  curl -s -w "%{http_code}\n" -o /dev/null \
    -H "x-api-key: dev_key_123" \
    "http://localhost:8000/api/v1/echo?msg=test"
done
```

Expected output (with `THROTTLE_RATE_LIMIT=3`):

```
200
200
200
429
429
```

### Reset counters between demo runs

```bash
bash scripts/reset_redis.sh
```

Flushes all Redis rate-limit keys instantly — no need to wait for the window TTL to expire.

### Inspect headers on a rate-limited response

```bash
curl -i -H "x-api-key: dev_key_123" http://localhost:8000/api/v1/echo
```

### Query metrics

```bash
curl -H "x-api-key: dev_key_123" http://localhost:8000/admin/metrics | python3 -m json.tool
```

### Query events

```bash
curl -H "x-api-key: dev_key_123" http://localhost:8000/admin/events | python3 -m json.tool
```

---

## Configuration

All settings are read from environment variables (or `.env`):

| Variable                   | Default                    | Description                      |
| -------------------------- | -------------------------- | -------------------------------- |
| `THROTTLE_ENV`             | `dev`                      | Environment name                 |
| `THROTTLE_API_KEYS`        | `dev_key_123`              | Comma-separated valid API keys   |
| `THROTTLE_REQUIRE_API_KEY` | `true`                     | Enforce auth on protected routes |
| `THROTTLE_REDIS_URL`       | `redis://localhost:6379/0` | Redis connection URL             |
| `THROTTLE_RATE_LIMIT`      | `3`                        | Max requests per window          |
| `THROTTLE_WINDOW_SECONDS`  | `60`                       | Window duration in seconds       |

For demos, setting `THROTTLE_RATE_LIMIT=3` makes it easy to trigger 429s quickly.

---

## Tech Stack

- **FastAPI** — API framework and middleware
- **Redis** — rate-limit counter storage
- **Docker / Docker Compose** — containerized full-stack setup
- **Pydantic Settings** — typed, validated configuration
- **Vanilla JS + HTML** — dashboard UI (no build step)

---

## Design Decisions

- **Single middleware** handles all gateway concerns (auth, rate limiting, error formatting, headers). This makes the request lifecycle easy to trace and explain.
- **Fixed-window rate limiting** chosen for clarity. The INCR + EXPIRE pattern is well-known and easy to reason about in interviews.
- **In-memory metrics/events** reset on restart. Acceptable for demo scope; a production deployment would use Redis or an external metrics system.
- **Admin endpoints not rate-limited** so the dashboard and monitoring remain usable while a key is throttled.
- **Standardized error envelope** (`{ "error": { "code", "message", "details", "request_id", "timestamp", "path" } }`) on all error responses.

---

## Future Improvements

- **Sliding window rate limiting** — use a Redis sorted set (ZADD / ZRANGEBYSCORE) to count requests in a true rolling window, eliminating the boundary burst problem of fixed windows
- **Token bucket** — allow short bursts while enforcing a steady-state average; better for APIs with bursty-but-legitimate traffic patterns
- **Redis-backed metrics** — persist counters to Redis so they survive restarts and can be read from multiple instances
- **Per-endpoint rate limits** — different limits for `/api/v1/expensive` vs `/api/v1/cheap` using route-specific config
- **Prometheus / OpenTelemetry** — expose a `/metrics` scrape endpoint for integration with Grafana dashboards
- **Admin-only API keys** — separate key roles so dashboard access doesn't share a key with rate-limited client traffic
