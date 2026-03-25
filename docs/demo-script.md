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
