import threading
import time
from dataclasses import dataclass, field
from typing import Dict


def mask_key(api_key: str) -> str:
    """Truncate key to first 3 chars + *** so secrets never appear in logs or dashboards."""
    if not api_key:
        return ""
    return api_key[:3] + "***"


@dataclass
class MetricsSnapshot:
    total_requests: int
    allowed_requests: int
    blocked_requests: int
    auth_missing: int
    auth_invalid: int
    requests_by_key: Dict[str, int] = field(default_factory=dict)
    blocked_by_key: Dict[str, int] = field(default_factory=dict)
    generated_at_epoch: int = field(default_factory=lambda: int(time.time()))


class MetricsStore:
    """
    Thread-safe in-memory counters.
    Stored in-memory intentionally — metrics reset on restart, which is acceptable
    for a demo. A production system would use Redis or Prometheus.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests = 0
        self._allowed_requests = 0
        self._blocked_requests = 0
        self._auth_missing = 0
        self._auth_invalid = 0
        self._requests_by_key: Dict[str, int] = {}
        self._blocked_by_key: Dict[str, int] = {}

    def inc_total(self) -> None:
        with self._lock:
            self._total_requests += 1

    def inc_allowed(self, api_key: str) -> None:
        mk = mask_key(api_key)
        with self._lock:
            self._allowed_requests += 1
            self._requests_by_key[mk] = self._requests_by_key.get(mk, 0) + 1

    def inc_blocked(self, api_key: str) -> None:
        mk = mask_key(api_key)
        with self._lock:
            self._blocked_requests += 1
            self._blocked_by_key[mk] = self._blocked_by_key.get(mk, 0) + 1

    def inc_auth_missing(self) -> None:
        with self._lock:
            self._auth_missing += 1

    def inc_auth_invalid(self) -> None:
        with self._lock:
            self._auth_invalid += 1

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(
                total_requests=self._total_requests,
                allowed_requests=self._allowed_requests,
                blocked_requests=self._blocked_requests,
                auth_missing=self._auth_missing,
                auth_invalid=self._auth_invalid,
                requests_by_key=dict(self._requests_by_key),
                blocked_by_key=dict(self._blocked_by_key),
            )


metrics = MetricsStore()
