#!/usr/bin/env bash
# Populate the dashboard with pre-demo activity, then reset Redis counters.
#
# After running this:
#   - Dashboard shows real metrics history (allowed + blocked counts, per-key rows)
#   - Events table has recent 429 entries
#   - Redis rate-limit counters are cleared so the live demo starts from count=0
#
# Usage:
#   bash scripts/seed.sh [base_url]

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
TMPFILE=$(mktemp /tmp/throttle_seed.XXXXXX)

trap 'rm -f "$TMPFILE"' EXIT

# Check the server is up before seeding
if ! curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
  echo "Error: server is not responding at $BASE_URL"
  echo "Start it first: make start"
  exit 1
fi

echo "Seeding dashboard with pre-demo activity..."

send() {
  local key="$1"
  local msg="$2"
  curl -s -o "$TMPFILE" -w "%{http_code}" \
    -H "x-api-key: $key" \
    "$BASE_URL/api/v1/echo?msg=$msg" > /dev/null
}

# 3 allowed requests with dev_key_123 (hits the limit exactly)
echo "  Sending 3 allowed requests with dev_key_123..."
send dev_key_123 seed1
send dev_key_123 seed2
send dev_key_123 seed3

# 3 more with dev_key_123 — these will be 429s, populating the events table
echo "  Sending 3 rate-limited requests with dev_key_123 (to populate events)..."
send dev_key_123 seed4
send dev_key_123 seed5
send dev_key_123 seed6

# 3 allowed requests with dev_key_456 (second key for per-key table)
echo "  Sending 3 allowed requests with dev_key_456..."
send dev_key_456 seed1
send dev_key_456 seed2
send dev_key_456 seed3

# 2 more with dev_key_456 — 429s for variety
echo "  Sending 2 rate-limited requests with dev_key_456..."
send dev_key_456 seed4
send dev_key_456 seed5

# Send a request with a missing key and one with a bad key
echo "  Sending 1 auth-missing and 1 auth-invalid request..."
curl -s -o /dev/null "$BASE_URL/api/v1/echo" || true
curl -s -o /dev/null -H "x-api-key: bad_key_xyz" "$BASE_URL/api/v1/echo" || true

echo ""
echo "Seeding complete. Resetting Redis counters so demo starts clean..."
bash "$(dirname "$0")/reset_redis.sh"

echo ""
echo "Dashboard is ready: $BASE_URL/dashboard"
echo "Run the demo: make demo"
