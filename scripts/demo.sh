#!/usr/bin/env bash
# Run the rate-limit demo against a running Throttle server.
#
# Usage:
#   bash scripts/demo.sh [api_key] [base_url]
#
# Defaults:
#   api_key  = dev_key_123
#   base_url = http://localhost:8000

set -euo pipefail

API_KEY="${1:-dev_key_123}"
BASE_URL="${2:-http://localhost:8000}"
ENDPOINT="$BASE_URL/api/v1/echo?msg=demo"
TMPFILE=$(mktemp /tmp/throttle_response.XXXXXX)

trap 'rm -f "$TMPFILE"' EXIT

echo "Throttle rate-limit demo"
echo "  API key : $API_KEY"
echo "  Endpoint: $ENDPOINT"
echo ""

for i in 1 2 3 4 5; do
  # Capture status code separately; body goes to temp file
  status=$(curl -s -o "$TMPFILE" -w "%{http_code}" \
    -H "x-api-key: $API_KEY" \
    "$ENDPOINT")
  body=$(cat "$TMPFILE")

  if [ "$status" = "200" ]; then
    echo "  Request $i -> 200 OK"
  elif [ "$status" = "429" ]; then
    retry_after=$(echo "$body" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('details',{}).get('retry_after','?'))" \
      2>/dev/null || echo "?")
    echo "  Request $i -> 429 Too Many Requests  (retry after ${retry_after}s)"
  else
    echo "  Request $i -> $status"
    echo "  Body: $body"
  fi
done

echo ""
echo "Open the dashboard: $BASE_URL/dashboard"
echo "To reset and run again: make reset && make demo"
