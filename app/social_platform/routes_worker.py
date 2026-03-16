import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.workers.worker_registry import WorkerRegistry
from app.social_platform.queue.job_queue_service import JobQueueService
from app.social_platform.infrastructure.event_store import EventStore

logger = logging.getLogger("routes_worker")

router = APIRouter(prefix="/admin", tags=["workers"])

_registry = WorkerRegistry()
_queue_service = JobQueueService()
_event_store = EventStore()


class RegisterWorkerRequest(BaseModel):
    hostname: str = Field(..., min_length=1)
    capabilities: List[str] = Field(default_factory=list)


class HeartbeatRequest(BaseModel):
    worker_id: str = Field(..., min_length=1)


class EnqueueRequest(BaseModel):
    proposal_id: str = Field(..., min_length=1)


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


def _validate_proposal_approved(proposal_id: str) -> dict:
    events = _event_store.get_events_by_domain("platform", limit=500)
    created = None
    approved = False
    for e in events:
        p = e.payload or {}
        if p.get("proposal_id") == proposal_id:
            if e.event_type == "proposal_created":
                created = p
            elif e.event_type == "proposal_approved":
                approved = True
    if not created:
        raise ValueError(f"Proposal {proposal_id} not found in event store")
    if not approved:
        raise ValueError(f"Proposal {proposal_id} is not approved — cannot enqueue")
    return created


@router.post("/queue/enqueue")
async def enqueue_job(request: EnqueueRequest):
    try:
        proposal_data = _validate_proposal_approved(request.proposal_id)

        action = proposal_data.get("action", "unknown")
        tool_payload = proposal_data.get("tool_payload", {})

        job = _queue_service.enqueue_job({
            "proposal_id": request.proposal_id,
            "action": action,
            "tool_name": action,
            "payload": tool_payload,
        })
        return {"job_id": job["id"], "status": "enqueued", "action": action}
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        logger.error(f"Enqueue failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
