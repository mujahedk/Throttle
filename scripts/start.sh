#!/usr/bin/env bash
# Start Throttle (Redis + API) and wait until the API is ready.
#
# Usage:
#   bash scripts/start.sh

set -euo pipefail

echo "Starting Throttle..."

if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not installed or not in PATH."
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "Error: Docker daemon is not running. Start Docker Desktop and try again."
  exit 1
fi

# Build and start containers in detached mode
docker compose up --build -d

echo "Waiting for API to be ready..."
max_attempts=30
attempt=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo ""
    echo "Error: API did not become ready after ${max_attempts} attempts."
    echo "Check logs with: docker compose logs api"
    exit 1
  fi
  printf "."
  sleep 2
done

echo ""
echo "Throttle is running."
echo ""
echo "  Dashboard : http://localhost:8000/dashboard"
echo "  API docs  : http://localhost:8000/docs"
echo "  Health    : http://localhost:8000/health"
echo ""
echo "Next steps:"
echo "  make seed   # populate dashboard with pre-demo activity"
echo "  make demo   # run the rate-limit demo loop"
echo "  make logs   # tail API logs"
echo "  make stop   # shut everything down"
