# Demo Script

A step-by-step guide for running Throttle live in an interview or portfolio demo.
Total time from cold start to running demo: under 3 minutes.

---

## 1. Start the project

```bash
cd api
make start
```

This builds and starts both Redis and the API in Docker, then waits until the API is healthy. When it prints the URLs, you're ready.

Expected output:
```
Throttle is running.

  Dashboard : http://localhost:8000/dashboard
  API docs  : http://localhost:8000/docs
  Health    : http://localhost:8000/health
```

If you don't have `make`, run directly:
```bash
bash scripts/start.sh
```

---

## 2. Populate the dashboard (pre-demo activity)

```bash
make seed
```

This fires ~14 requests across two API keys — a mix of allowed and rate-limited — so the dashboard shows real data before the live demo starts. It then resets the Redis counters so the demo begins from a clean state.

---

## 3. Open the dashboard

```
http://localhost:8000/dashboard
```

The dashboard auto-authenticates with `dev_key_123` on first load — no manual key entry needed. You should see:

- **Total Requests**: ~16 (from seeding + health check)
- **Allowed**: ~8
- **Blocked (429)**: ~5
- **Requests by Key**: `dev***` and `dev***` rows
- **Recent Rate Limit Events**: table populated with 429 entries

Keep this tab open during the demo. It auto-refreshes every 2 seconds.

---

## 4. Run the live demo

Open a terminal and run:

```bash
make demo
```

Expected output:
```
Throttle rate-limit demo
  API key : dev_key_123
  Endpoint: http://localhost:8000/api/v1/echo?msg=demo

  Request 1 -> 200 OK
  Request 2 -> 200 OK
  Request 3 -> 200 OK
  Request 4 -> 429 Too Many Requests  (retry after 47s)
  Request 5 -> 429 Too Many Requests  (retry after 47s)
```

Watch the dashboard update in real time as each request lands.

---

## 5. Show the headers directly

```bash
curl -i -H "x-api-key: dev_key_123" http://localhost:8000/api/v1/echo
```

Point out the response headers:
```
HTTP/1.1 200 OK
X-Request-Id: <uuid>
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 2
X-RateLimit-Reset: <epoch timestamp>
```

After exceeding the limit:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 0
X-RateLimit-Reset: <epoch>
Retry-After: <seconds>
```

---

## 6. Show auth enforcement

```bash
# Missing key -> 401
curl -i http://localhost:8000/api/v1/echo

# Invalid key -> 403
curl -i -H "x-api-key: wrong_key" http://localhost:8000/api/v1/echo
```

Point out the consistent JSON error envelope: `code`, `message`, `request_id`, `timestamp`, `path`.

---

## 7. Reset and repeat

```bash
make reset
```

Flushes Redis counters instantly — no waiting for the 60-second TTL. Run `make demo` again immediately.

---

## 8. Shut down

```bash
make stop
```

---

## What to Say

### 30-second version

> Throttle is a FastAPI gateway that enforces per-API-key rate limits using Redis. Every request goes through a single middleware that validates the API key, increments a Redis counter for the current time window, and returns a 429 with standard rate-limit headers if the limit is exceeded. There's a live dashboard that shows throughput, blocked requests, and recent rate-limit events.

### 2-minute version

> The core is a single HTTP middleware in `main.py` that handles everything: auth, rate limiting, metrics, and response headers. Auth is checked first — missing or invalid keys get 401 or 403 before Redis is ever touched.
>
> For valid keys, I call `check_rate_limit()` in `core/rate_limit.py`. It does an atomic `INCR` on a Redis key namespaced as `rl:<api_key>:<window_id>`, where `window_id = unix_timestamp // window_seconds`. On the first request in a window, it also calls `EXPIRE` to set the TTL. If the count exceeds the limit, the middleware returns a 429 with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` headers.
>
> I chose fixed-window rate limiting because it's one Redis operation per request and easy to reason about. The trade-off is that a client can burst 2x the limit across a window boundary — which sliding window or token bucket would prevent, at the cost of more Redis complexity.
>
> The dashboard polls `/admin/metrics` and `/admin/events` every 2 seconds and shows per-key throughput and rate-limit event history. The metrics are in-memory — a deliberate simplification for this scope.

### 5-minute version

Walk through these points in order, opening files as you go:

1. **Request lifecycle** — open `app/main.py`, show `EXEMPT_PATHS` and `NO_RATE_LIMIT_PATHS` at the top, then walk the middleware top to bottom
2. **Auth logic** — exempt paths skip auth; admin paths require auth but skip rate limiting; everything else gets both
3. **Redis key design** — open `app/core/rate_limit.py`, show `make_redis_key()` and `check_rate_limit()`. Then: `docker exec -it throttle-redis redis-cli keys "rl:*"` to show live keys
4. **Fixed-window trade-off** — INCR is O(1) and atomic. The boundary burst: 10 requests at second 59 + 10 at second 61 = 20 in 2 seconds against a 10/60s limit. Sliding window (ZADD/ZRANGEBYSCORE) solves this at the cost of more ops
5. **Standardized errors** — open `app/core/errors.py`, show `APIError.to_dict()`. Every error (401, 403, 429, 500) produces the same envelope
6. **Dashboard + observability** — open `app/core/metrics.py` and `app/core/events.py`. Metrics are thread-safe in-memory counters. Production path: push to Redis with INCR or expose a Prometheus `/metrics` endpoint

---

## Useful Commands During a Demo

```bash
# Watch Redis activity in real time
docker exec -it throttle-redis redis-cli monitor

# Check current rate-limit keys
docker exec -it throttle-redis redis-cli keys "rl:*"

# Check the count for a specific key (replace <window_id> with the value from keys above)
docker exec -it throttle-redis redis-cli get "rl:dev_key_123:<window_id>"

# Query metrics directly
curl -s -H "x-api-key: dev_key_123" http://localhost:8000/admin/metrics | python3 -m json.tool

# Query events directly
curl -s -H "x-api-key: dev_key_123" http://localhost:8000/admin/events | python3 -m json.tool

# Tail API logs
make logs
```
