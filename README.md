Throttle

Throttle is a lightweight API gateway that enforces per-API-key rate limiting, returns standardized error responses, and exposes real-time observability through metrics and a live dashboard.

It’s designed as a production-minded MVP: simple, defensive, and explainable end-to-end.

✨ What Throttle Does

Accepts API requests

Authenticates clients using API keys

Enforces per-key rate limits using Redis

Returns proper HTTP 429 responses with standard rate-limit headers

Tracks request metrics and rate-limit events

Provides a live dashboard for observability

This mirrors how real API platforms (Stripe, Cloudflare, Vercel, etc.) protect and monitor their APIs.

🧠 Why This Project Exists

Almost every real backend system needs:

rate limiting

defensive error handling

observability

admin tooling

Throttle focuses on those infrastructure fundamentals, rather than application-specific business logic.

The goal is to demonstrate:

systems thinking

correctness under load

clean separation of concerns

explainable design decisions

🏗️ Architecture Overview
Client
↓
FastAPI Middleware
├─ Request ID assignment
├─ API key authentication
├─ Redis-backed rate limiting
├─ Metrics + event logging
↓
Route handler
↓
Standardized response + headers

Redis is used only for rate limiting.
Metrics and events are stored in memory for simplicity (MVP choice).

🔐 Authentication

Protected endpoints require an API key:

x-api-key: <your_key>

Example keys are configured via environment variables.

Behavior:

Missing key → 401 AUTH_MISSING

Invalid key → 403 AUTH_INVALID

🚦 Rate Limiting

Strategy: Fixed window per API key

Backend: Redis

Mechanism: INCR + EXPIRE

Example behavior (limit = 3 requests / 60s):

200 OK
200 OK
200 OK
429 Too Many Requests
429 Too Many Requests

Rate-limit headers returned

X-RateLimit-Limit

X-RateLimit-Remaining

X-RateLimit-Reset

Retry-After

These allow clients to back off intelligently.

📊 Observability

Throttle exposes two admin endpoints:

GET /admin/metrics

Returns a snapshot of counters:

total requests

allowed requests

blocked requests

auth failures

per-key request counts

GET /admin/events

Returns recent rate-limit events:

timestamp

request path

masked API key

retry-after

reset time

request count

Admin endpoints:

require API key

are not rate-limited (so you can observe during throttling)

🖥️ Dashboard

A simple dashboard is available at:

http://localhost:8000/dashboard

Features:

KPI cards (total / allowed / blocked / auth failures)

Requests by API key

Blocked requests by API key

Recent rate-limit events table

Auto-refresh every 2 seconds

The dashboard UI is public, but data loads only after entering a valid API key.

🚀 Getting Started

1. Clone the repo
   git clone <repo-url>
   cd throttle

2. Start Redis
   docker compose up -d

Verify:

docker exec -it throttle-redis redis-cli ping

# PONG

3. Set up the API
   cd api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

Create .env:

THROTTLE_ENV=dev
THROTTLE_API_KEYS=dev_key_123
THROTTLE_RATE_LIMIT=3
THROTTLE_WINDOW_SECONDS=60
THROTTLE_REDIS_URL=redis://localhost:6379/0

4. Run the server
   uvicorn app.main:app --reload --port 8000

🧪 Quick Demo
Health check
curl http://localhost:8000/health

Rate limit demo
for i in 1 2 3 4 5; do
curl -s -o /dev/null -w "%{http_code}\n" \
 -H "x-api-key: dev_key_123" \
 "http://localhost:8000/api/v1/echo?msg=yo"
done

Metrics
curl -H "x-api-key: dev_key_123" http://localhost:8000/admin/metrics

Events
curl -H "x-api-key: dev_key_123" http://localhost:8000/admin/events

🛠️ Tech Stack

FastAPI – API framework

Redis – rate limiting backend

Docker – Redis containerization

Vanilla JS + HTML – dashboard UI

🧩 Design Decisions

Fixed window chosen for clarity and explainability

Redis used only where persistence matters

In-memory metrics/events for MVP simplicity

Single middleware for request control flow

Standardized error envelopes for consistency

🔮 Future Improvements

Sliding window or token bucket rate limiting

Redis-backed metrics/events for persistence

React dashboard (v2)

Per-endpoint limits

Admin-only API keys

Prometheus / OpenTelemetry export

📌 Summary

Throttle is a focused systems project that demonstrates:

defensive backend engineering

rate limiting correctness

observability

clean architecture

real-world API behavior

It’s intentionally small, but intentionally real.
