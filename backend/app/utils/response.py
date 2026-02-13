from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """모든 API 응답의 공통 래퍼"""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def success_response(
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
) -> ApiResponse:
    return ApiResponse(success=True, data=data, meta=meta)


def error_response(
    error: str,
    error_code: Optional[str] = None,
) -> ApiResponse:
    return ApiResponse(success=False, error=error, error_code=error_code)
