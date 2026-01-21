from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class APIError(Exception):
    status_code: int
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self, request_id: str, path: str) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details or {},
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": path,
            }
        }
