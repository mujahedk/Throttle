from fastapi import APIRouter, Query

from app.core.metrics import metrics
from app.core.events import events

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
def get_metrics():
    """
    Return a point-in-time snapshot of counters.

    Why snapshot?
    - We want stable values at the moment of the request.
    - The underlying counters can continue changing while we respond.
    """
    snap = metrics.snapshot()
    return {
        "generated_at_epoch": snap.generated_at_epoch,
        "total_requests": snap.total_requests,
        "allowed_requests": snap.allowed_requests,
        "blocked_requests": snap.blocked_requests,
        "auth_missing": snap.auth_missing,
        "auth_invalid": snap.auth_invalid,
        "requests_by_key": snap.requests_by_key,
        "blocked_by_key": snap.blocked_by_key,
    }


@router.get("/events")
def get_events(limit: int = Query(default=50, ge=1, le=200)):
    """
    Return most recent rate-limit events first.

    Query param:
      - limit: how many events to return (1..200)

    We cap at 200 to avoid returning massive payloads.
    """
    return {"events": events.list_events(limit=limit)}
