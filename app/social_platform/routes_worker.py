import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.workers.worker_registry import WorkerRegistry
from app.social_platform.queue.job_queue_service import JobQueueService

logger = logging.getLogger("routes_worker")

router = APIRouter(prefix="/admin", tags=["workers"])

_registry = WorkerRegistry()
_queue_service = JobQueueService()


class RegisterWorkerRequest(BaseModel):
    hostname: str = Field(..., min_length=1)
    capabilities: List[str] = Field(default_factory=list)


class HeartbeatRequest(BaseModel):
    worker_id: str = Field(..., min_length=1)


class EnqueueRequest(BaseModel):
    action: str = Field(..., min_length=1)
    payload: dict = Field(default_factory=dict)
    proposal_id: str = Field(default="")


@router.get("/workers")
async def list_workers():
    workers = _registry.list_workers()
    queue_depth = _queue_service.get_queue_depth()
    dlq = _queue_service.list_dlq(limit=20)
    return {
        "workers": workers,
        "queue_depth": queue_depth,
        "dead_letter_queue": dlq,
        "total_workers": len(workers),
    }


@router.get("/workers/{worker_id}")
async def get_worker(worker_id: str):
    worker = _registry.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.get("/queue")
async def get_queue_overview():
    depth = _queue_service.get_queue_depth()
    stats = _queue_service.get_stats()
    dlq = _queue_service.list_dlq(limit=20)
    return {
        "depth": depth,
        "stats": stats,
        "dead_letter_queue": dlq,
    }


@router.get("/queue/depth")
async def get_queue_depth():
    return _queue_service.get_queue_depth()


@router.get("/queue/jobs")
async def get_queue_jobs(status: Optional[str] = None, limit: int = 50):
    return {"jobs": _queue_service.list_jobs(limit=limit, status=status)}


@router.post("/workers/register")
async def register_worker(request: RegisterWorkerRequest):
    worker = _registry.register_worker(request.hostname, request.capabilities)
    return worker


@router.post("/workers/heartbeat")
async def worker_heartbeat(request: HeartbeatRequest):
    result = _registry.heartbeat(request.worker_id)
    if not result:
        raise HTTPException(status_code=404, detail="Worker not found")
    return result


@router.post("/queue/enqueue")
async def enqueue_job(request: EnqueueRequest):
    try:
        job = _queue_service.enqueue_job({
            "proposal_id": request.proposal_id or str(uuid.uuid4()),
            "action": request.action,
            "tool_name": request.action,
            "payload": request.payload,
        })
        return {"job_id": job["id"], "status": "enqueued", "action": request.action}
    except Exception as exc:
        logger.error(f"Enqueue failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
