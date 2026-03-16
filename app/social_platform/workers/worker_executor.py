import uuid
import time
import logging
from typing import Optional

from app.social_platform.queue.job_queue_service import JobQueueService
from app.social_platform.workers.worker_registry import WorkerRegistry
from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.agent_runtime.tool_registry import ToolRegistry

logger = logging.getLogger("worker_executor")

SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


class WorkerExecutor:
    def __init__(
        self,
        worker_id: str,
        queue_service: JobQueueService,
        registry: WorkerRegistry,
        event_store: EventStore,
        tool_registry: ToolRegistry,
        execution_engine=None,
        poll_interval: float = 2.0,
        heartbeat_interval: float = 10.0,
    ):
        self._worker_id = worker_id
        self._queue = queue_service
        self._registry = registry
        self._event_store = event_store
        self._tool_registry = tool_registry
        self._execution_engine = execution_engine
        self._poll_interval = poll_interval
        self._heartbeat_interval = heartbeat_interval
        self._running = False
        self._last_heartbeat = 0.0

    def _emit_event(self, event_type: str, payload: dict):
        try:
            self._event_store.append_event(
                domain="worker",
                event_type=event_type,
                actor_id=SYSTEM_ACTOR_ID,
                payload=payload,
            )
        except Exception as exc:
            logger.error(f"Failed to emit event {event_type}: {exc}")

    def _heartbeat(self):
        now = time.time()
        if now - self._last_heartbeat >= self._heartbeat_interval:
            self._registry.heartbeat(self._worker_id)
            self._emit_event("worker_heartbeat", {
                "worker_id": self._worker_id,
            })
            self._last_heartbeat = now

    def _execute_job(self, job: dict):
        job_id = job["id"]
        proposal_id = job["proposal_id"]
        tool_name = job["tool_name"]

        self._emit_event("job_claimed", {
            "job_id": job_id,
            "worker_id": self._worker_id,
            "proposal_id": proposal_id,
            "tool_name": tool_name,
        })

        self._registry.assign_job(self._worker_id, job_id)
        self._queue.update_job_status(job_id, "running")

        self._emit_event("job_started", {
            "job_id": job_id,
            "worker_id": self._worker_id,
            "tool_name": tool_name,
        })

        try:
            payload = job.get("payload", {})
            raw_tool_name = payload.get("tool_name", tool_name)
            if raw_tool_name.startswith("tool_"):
                raw_tool_name = raw_tool_name[5:]
            args = payload.get("arguments", {})

            tool = self._tool_registry.get(raw_tool_name)
            if tool:
                result = tool.execute(**args)
                logger.info(f"Job {job_id}: executed tool '{raw_tool_name}' via ToolRegistry")
            elif self._execution_engine:
                action = job.get("tool_name", "unknown")
                execution_result = self._execution_engine.execute_from_payload(
                    action=action,
                    payload=payload,
                    proposal_id=proposal_id,
                    worker_id=f"queue_worker_{self._worker_id[:8]}",
                )
                result = execution_result.get("result", {})
            else:
                result = {"status": "completed", "message": f"Tool {tool_name} executed (no engine)"}

            self._queue.update_job_status(job_id, "completed")
            self._emit_event("job_completed", {
                "job_id": job_id,
                "worker_id": self._worker_id,
                "tool_name": tool_name,
                "result_status": "success",
            })
            logger.info(f"Job {job_id} completed successfully")

        except Exception as exc:
            logger.error(f"Job {job_id} failed: {exc}")
            job_result = self._queue.fail_job(job_id, str(exc))

            if job_result and job_result.get("status") == "dlq":
                self._emit_event("job_dlq", {
                    "job_id": job_id,
                    "worker_id": self._worker_id,
                    "tool_name": tool_name,
                    "error": str(exc),
                    "retry_count": job_result.get("retry_count", 0),
                })
            else:
                self._emit_event("job_failed", {
                    "job_id": job_id,
                    "worker_id": self._worker_id,
                    "tool_name": tool_name,
                    "error": str(exc),
                    "retry_count": job_result.get("retry_count", 0) if job_result else 0,
                })
        finally:
            self._registry.release_job(self._worker_id)

    def run(self):
        self._running = True
        logger.info(f"Worker executor {self._worker_id} started (poll={self._poll_interval}s)")

        self._emit_event("worker_registered", {
            "worker_id": self._worker_id,
        })

        while self._running:
            try:
                self._heartbeat()
                job = self._queue.claim_job(self._worker_id)
                if job:
                    self._execute_job(job)
                else:
                    time.sleep(self._poll_interval)
            except KeyboardInterrupt:
                logger.info("Worker executor interrupted")
                break
            except Exception as exc:
                logger.error(f"Worker loop error: {exc}")
                time.sleep(self._poll_interval)

        self._running = False
        self._registry.update_status(self._worker_id, "idle")
        logger.info(f"Worker executor {self._worker_id} stopped")

    def stop(self):
        self._running = False
