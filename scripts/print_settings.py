"""Print resolved settings. Run from the api/ directory: python scripts/print_settings.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

print(f"ENV:              {settings.throttle_env}")
print(f"REQUIRE_API_KEY:  {settings.throttle_require_api_key}")
print(f"API_KEYS:         {settings.api_key_set}")
print(f"REDIS_URL:        {settings.throttle_redis_url}")
print(f"RATE_LIMIT:       {settings.throttle_rate_limit} req / {settings.throttle_window_seconds}s")
