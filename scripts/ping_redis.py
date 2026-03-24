"""Verify Redis connectivity. Run from the api/ directory: python scripts/ping_redis.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.redis_client import get_redis_client

r = get_redis_client()
result = r.ping()
print("Redis PING →", result)
