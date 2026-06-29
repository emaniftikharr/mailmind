import time

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])

_started_at = time.time()


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", uptime_seconds=round(time.time() - _started_at, 2))
