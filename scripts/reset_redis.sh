#!/usr/bin/env bash
# Flush all rate-limit keys from Redis so demo counters reset instantly.
#
# Usage:
#   bash scripts/reset_redis.sh
#
# Requires the throttle-redis container to be running (docker compose up -d redis).

CONTAINER="${1:-throttle-redis}"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "Error: container '$CONTAINER' is not running."
  echo "Start it with: docker compose up -d redis"
  exit 1
fi

docker exec "$CONTAINER" redis-cli FLUSHDB
echo "Redis flushed. Rate-limit counters and metrics reset."
