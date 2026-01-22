from redis import Redis
from app.core.config import settings


def get_redis_client() -> Redis:
    """
    Create a Redis client using the configured Redis URL.

    decode_responses=True means:
      - Redis returns strings instead of bytes
      - Makes debugging and JSON logging much easier
    """
    return Redis.from_url(settings.throttle_redis_url, decode_responses=True)
