from fastapi import APIRouter, Request

router = APIRouter()


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
