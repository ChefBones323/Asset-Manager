import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.agent_runtime.agent_runtime import AgentRuntime
from app.social_platform.infrastructure.event_store import EventStore

logger = logging.getLogger("agent_runtime.routes")

router = APIRouter(prefix="/admin/agent", tags=["agent_runtime"])

_runtime: Optional[AgentRuntime] = None


def _get_runtime() -> AgentRuntime:
    global _runtime
    if _runtime is None:
        event_store = EventStore()
        _runtime = AgentRuntime(event_store=event_store)
    return _runtime


class RunTaskRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=2000, description="User task description")


class MemoryStoreRequest(BaseModel):
    category: str = Field(..., description="Memory category")
    key: str = Field(..., description="Memory key")
    value: str = Field(..., description="Memory value")


@router.post("/run")
def run_agent_task(request: RunTaskRequest):
    try:
        runtime = _get_runtime()
        result = runtime.run_task(request.task)
        return result
    except Exception as exc:
        logger.error(f"Agent task failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/memory")
def get_agent_memory(category: Optional[str] = None, limit: int = 50):
    try:
        runtime = _get_runtime()
        memories = runtime.memory_service.retrieve(category=category, limit=limit)
        return {"memories": memories, "total": len(memories)}
    except Exception as exc:
        logger.error(f"Memory retrieval failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/memory")
def store_agent_memory(request: MemoryStoreRequest):
    try:
        runtime = _get_runtime()
        memory = runtime.memory_service.store(
            category=request.category,
            key=request.key,
            value=request.value,
        )
        return memory
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Memory store failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/memory/{memory_id}")
def delete_agent_memory(memory_id: str):
    try:
        runtime = _get_runtime()
        deleted = runtime.memory_service.delete(memory_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"status": "deleted", "id": memory_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Memory delete failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tools")
def list_agent_tools():
    runtime = _get_runtime()
    return {
        "tools": runtime.tool_registry.list_tools(),
        "policies": runtime.policy_guard.list_policies(),
    }


@router.get("/scheduler")
def get_scheduler_status():
    runtime = _get_runtime()
    return {
        "running": runtime.scheduler.is_running,
        "tasks": runtime.scheduler.list_tasks(),
    }


@router.post("/scheduler/{task_id}/run")
def run_scheduled_task(task_id: str):
    runtime = _get_runtime()
    result = runtime.scheduler.run_task_now(task_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
