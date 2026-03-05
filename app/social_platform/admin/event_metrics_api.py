from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.social_platform.infrastructure.event_metrics import EventMetrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/event_metrics")
async def event_metrics(
    window: int = Query(60, ge=1, le=3600, description="Time window in seconds"),
):
    metrics = EventMetrics()
    return metrics.compute_metrics(window_seconds=window)
