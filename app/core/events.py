import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.metrics import mask_key


@dataclass
class RateLimitEvent:
    timestamp_epoch: int
    request_id: str
    path: str
    api_key_masked: str
    status_code: int = 429
    details: Dict[str, Any] = field(default_factory=dict)


class EventStore:
    """
    Thread-safe rolling buffer of rate-limit events.
    Keeps the most recent N events; oldest are dropped when full.
    """

    def __init__(self, max_events: int = 200) -> None:
        self._lock = threading.Lock()
        self._max_events = max_events
        self._events: List[RateLimitEvent] = []

    def add_rate_limit_event(
        self,
        request_id: str,
        path: str,
        api_key: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        evt = RateLimitEvent(
            timestamp_epoch=int(time.time()),
            request_id=request_id,
            path=path,
            api_key_masked=mask_key(api_key),
            details=details or {},
        )
        with self._lock:
            self._events.append(evt)
            if len(self._events) > self._max_events:
                self._events = self._events[len(self._events) - self._max_events:]

    def list_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            recent = list(reversed(self._events[-limit:]))
        return [
            {
                "timestamp_epoch": e.timestamp_epoch,
                "request_id": e.request_id,
                "path": e.path,
                "api_key": e.api_key_masked,
                "status_code": e.status_code,
                "details": e.details,
            }
            for e in recent
        ]


events = EventStore(max_events=200)
