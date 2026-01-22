from app.core.redis_client import get_redis_client

r = get_redis_client()
print("PING ->", r.ping())
