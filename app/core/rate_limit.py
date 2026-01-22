import time
from dataclasses import dataclass
from typing import Optional

from redis import Redis


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_epoch_seconds: int
    retry_after_seconds: Optional[int] = None
    current_count: int = 0


def current_window_id(window_seconds: int, now: Optional[int] = None) -> int:
    """
    Return the fixed-window bucket ID.

    Example: window_seconds=60
      - timestamps 0..59    -> window_id 0
      - timestamps 60..119  -> window_id 1
    """
    now = now if now is not None else int(time.time())
    return now // window_seconds


def make_redis_key(api_key: str, window_id: int) -> str:
    """
    Namespace keys so they are easy to inspect and don't collide with other app keys.
    """
    return f"rl:{api_key}:{window_id}"


def check_rate_limit(
    r: Redis,
    api_key: str,
    limit: int,
    window_seconds: int,
) -> RateLimitResult:
    """
    Fixed-window rate limiting:

    - INCR rl:<api_key>:<window_id>
    - EXPIRE when first created
    - If over limit: not allowed, compute retry-after and reset times
    """
    now = int(time.time())
    window_id = current_window_id(window_seconds, now=now)
    key = make_redis_key(api_key, window_id)

    # 1) Increase count atomically
    count = int(r.incr(key))

    # 2) Ensure key expires so the window resets
    if count == 1:
        r.expire(key, window_seconds)

    # 3) Compute window reset time (end of current window)
    window_start = window_id * window_seconds
    reset_epoch = window_start + window_seconds
    seconds_until_reset = max(0, reset_epoch - now)

    # remaining is how many requests are left BEFORE hitting the limit
    remaining = max(0, limit - count)

    if count > limit:
        return RateLimitResult(
            allowed=False,
            limit=limit,
            remaining=0,
            reset_epoch_seconds=reset_epoch,
            retry_after_seconds=seconds_until_reset,
            current_count=count,
        )

    return RateLimitResult(
        allowed=True,
        limit=limit,
        remaining=remaining,
        reset_epoch_seconds=reset_epoch,
        retry_after_seconds=None,
        current_count=count,
    )
