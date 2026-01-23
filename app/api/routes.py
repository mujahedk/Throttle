from fastapi import APIRouter, Request
from app.api.admin import router as admin_router
from app.api.dashboard import router as dashboard_router

router = APIRouter()

router.include_router(admin_router)
router.include_router(dashboard_router)


@router.get("/health")
def health():
    return {"status": "ok", "service": "throttle"}


@router.get("/api/v1/echo")
def echo(request: Request, msg: str = "hello"):
    api_key = getattr(request.state, "api_key", None)
    return {
        "ok": True,
        "msg": msg,
        "api_key_masked": (api_key[:3] + "***") if api_key else None,
    }
