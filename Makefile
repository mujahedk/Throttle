.PHONY: start stop restart logs demo seed reset clean

# Start Redis + API, wait until ready, print URLs
start:
	@bash scripts/start.sh

# Stop all containers
stop:
	docker compose down

# Stop and restart
restart: stop start

# Tail API logs
logs:
	docker compose logs -f api

# Run the rate-limit demo loop (server must be running)
demo:
	@bash scripts/demo.sh

# Populate dashboard with pre-demo activity, then reset Redis counters
seed:
	@bash scripts/seed.sh

# Flush Redis rate-limit counters (reset between demo runs)
reset:
	@bash scripts/reset_redis.sh

# Stop containers and remove volumes (full clean)
clean:
	docker compose down -v
