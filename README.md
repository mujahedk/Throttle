# Throttle

**Throttle** is a lightweight API gateway that enforces per-API-key rate limiting, returns standardized error responses, and exposes real-time observability through metrics and a live dashboard.

It is built as a **production-minded MVP**, focusing on the infrastructure problems that real backend systems must solve.

---

## ✨ Features

- API key authentication
- Redis-backed rate limiting (fixed window)
- Standardized error responses
- Proper HTTP `429 Too Many Requests` handling
- Rate-limit headers (`Retry-After`, `X-RateLimit-*`)
- Real-time metrics and event logging
- Admin API endpoints
- Live dashboard UI

---

## 🧠 Why Throttle?

Almost every real API needs:

- rate limiting
- defensive error handling
- observability
- operational visibility

Throttle focuses on these **backend fundamentals** rather than application-specific logic, making it an ideal demonstration of systems thinking and production readiness.

---

## 🏗️ Architecture Overview

```
Client
  ↓
FastAPI Middleware
  ├─ Request ID assignment
  ├─ API key authentication
  ├─ Redis-backed rate limiting
  ├─ Metrics + event logging
  ↓
Route handlers
  ↓
Standardized response + headers
```

- **Redis** is used for rate limiting
- **Metrics and events** are stored in memory (intentional MVP choice)

---

## 🔐 Authentication

Protected endpoints require an API key:

```http
x-api-key: <your_api_key>
```

Authentication behavior:

- Missing key → `401 AUTH_MISSING`
- Invalid key → `403 AUTH_INVALID`

---

## 🚦 Rate Limiting

- **Strategy:** Fixed window per API key
- **Backend:** Redis
- **Mechanism:** `INCR` + `EXPIRE`

Example behavior (limit = 3 requests / 60 seconds):

```
200 OK
200 OK
200 OK
429 Too Many Requests
429 Too Many Requests
```

### Rate-limit headers returned

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`
- `Retry-After`

These headers allow clients to back off intelligently.

---

## 📊 Observability (Admin API)

### `GET /admin/metrics`

Returns a snapshot of request counters:

- total requests
- allowed requests
- blocked requests
- authentication failures
- per-API-key request counts

### `GET /admin/events`

Returns recent rate-limit events, including:

- timestamp
- request path
- masked API key
- retry-after value
- reset time
- request count

Admin endpoints:

- require an API key
- are **not rate-limited**, so operators can observe during throttling

---

## 🖥️ Dashboard

The dashboard is available at:

```
http://localhost:8000/dashboard
```

### Dashboard features

- KPI cards:

  - Total Requests
  - Allowed Requests
  - Blocked Requests
  - Auth Missing
  - Auth Invalid

- Requests by API key
- Blocked requests by API key
- Recent rate-limit events table
- Auto-refresh every 2 seconds

The dashboard UI is public, but data loads only after providing a valid API key.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd throttle
```

---

### 2. Start Redis (Docker)

```bash
docker compose up -d
```

Verify Redis is running:

```bash
docker exec -it throttle-redis redis-cli ping
# PONG
```

---

### 3. Set up the API

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
THROTTLE_ENV=dev
THROTTLE_API_KEYS=dev_key_123
THROTTLE_RATE_LIMIT=3
THROTTLE_WINDOW_SECONDS=60
THROTTLE_REDIS_URL=redis://localhost:6379/0
```

---

### 4. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

---

## 🧪 Demo Commands

### Health check

```bash
curl http://localhost:8000/health
```

---

### Rate limit demo

```bash
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "x-api-key: dev_key_123" \
    "http://localhost:8000/api/v1/echo?msg=yo"
done
```

Expected output:

```
200
200
200
429
429
```

---

### Metrics

```bash
curl -H "x-api-key: dev_key_123" http://localhost:8000/admin/metrics
```

---

### Events

```bash
curl -H "x-api-key: dev_key_123" http://localhost:8000/admin/events
```

---

## 🛠️ Tech Stack

- **FastAPI** — API framework
- **Redis** — rate limiting backend
- **Docker** — Redis containerization
- **Vanilla JavaScript + HTML** — dashboard UI

---

## 🧩 Design Decisions

- Fixed-window rate limiting for clarity and correctness
- Redis used only where persistence is required
- In-memory metrics/events for MVP simplicity
- Single middleware controls request flow
- Standardized error envelopes for consistency

---

## 🔮 Future Improvements

- Sliding window or token bucket algorithms
- Redis-backed metrics and events
- React dashboard (v2)
- Per-endpoint rate limits
- Admin-only API keys
- Prometheus / OpenTelemetry integration

---

## 📌 Summary

Throttle is a focused systems project that demonstrates:

- defensive backend engineering
- rate limiting correctness
- observability
- clean architecture
- real-world API behavior

It is intentionally small — and intentionally **real**.

---
