import logging
from fastapi import APIRouter

from app.social_platform.workers.worker_registry import WorkerRegistry
from app.social_platform.queue.job_queue_service import JobQueueService

logger = logging.getLogger("worker_metrics")

router = APIRouter(tags=["metrics"])

_registry = WorkerRegistry()
_queue_service = JobQueueService()


@router.get("/metrics")
async def get_metrics():
    _registry.sweep_unhealthy(); worker_counts = _registry.get_counts()
    queue_stats = _queue_service.get_stats()
    queue_depth = _queue_service.get_queue_depth()

    return {
        "active_workers": worker_counts.get("idle", 0) + worker_counts.get("busy", 0),
        "busy_workers": worker_counts.get("busy", 0),
        "unhealthy_workers": worker_counts.get("unhealthy", 0),
        "total_workers": worker_counts.get("total", 0),
        "queue_depth": queue_depth.get("queued", 0),
        "queue_running": queue_depth.get("running", 0),
        "jobs_processed_total": queue_stats.get("jobs_processed_total", 0),
        "jobs_failed_total": queue_stats.get("jobs_failed_total", 0),
        "dlq_count": queue_stats.get("dlq_count", 0),
        "retry_rate": queue_stats.get("retry_rate", 0.0),
    }
