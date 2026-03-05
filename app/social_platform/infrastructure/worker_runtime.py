import uuid
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any, List

from pydantic import BaseModel, Field, field_validator, ValidationError

from app.social_platform.infrastructure.redis_queue import RedisQueue


class ManifestStep(BaseModel):
    step_id: str = Field(..., min_length=1)
    order: int = Field(..., ge=0)
    operation: str = Field(..., min_length=1)
    description: str = ""
    params: dict = Field(default_factory=dict)


class WorkerManifest(BaseModel):
    manifest_id: str = Field(..., min_length=1)
    proposal_id: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    actor_id: str = Field(..., min_length=1)
    payload: dict = Field(default_factory=dict)
    steps: List[ManifestStep] = Field(..., min_length=1)
    checksum: str = Field(..., min_length=1)

    @field_validator("steps")
    @classmethod
    def steps_must_be_ordered(cls, v: List[ManifestStep]) -> List[ManifestStep]:
        orders = [s.order for s in v]
        if orders != sorted(orders):
            raise ValueError("steps must be in ascending order")
        if len(set(orders)) != len(orders):
            raise ValueError("step orders must be unique")
        return v


class ManifestValidationError(Exception):
    def __init__(self, manifest_id: str, errors: list):
        self.manifest_id = manifest_id
        self.errors = errors
        detail = "; ".join(str(e) for e in errors[:5])
        super().__init__(f"Manifest {manifest_id} failed validation: {detail}")


class WorkerRuntime:
    def __init__(self, event_store=None, lease_manager=None, heartbeat_interval: float = 10.0):
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, RedisQueue] = {}
        self._running = False
        self._threads: Dict[str, threading.Thread] = {}
        self._heartbeat_threads: Dict[str, threading.Thread] = {}
        self._job_statuses: Dict[str, Dict[str, Any]] = {}
        self._event_store = event_store
        self._lease_manager = lease_manager
        self._heartbeat_interval = heartbeat_interval

    def validate_manifest(self, manifest: dict) -> WorkerManifest:
        manifest_id = manifest.get("manifest_id", "<unknown>")
        try:
            return WorkerManifest.model_validate(manifest)
        except ValidationError as exc:
            errors = exc.errors()
            self._transition_job(manifest_id, "failed", errors=errors)
            self._write_audit_record(
                manifest_id=manifest_id,
                action="manifest_validation_failed",
                details={"errors": [str(e) for e in errors[:10]]},
            )
            raise ManifestValidationError(manifest_id, errors) from exc

    def _write_audit_record(
        self,
        manifest_id: str,
        action: str,
        details: Optional[dict] = None,
    ):
        if not self._event_store:
            return
        try:
            self._event_store.append_event(
                domain="audit",
                event_type=f"worker_{action}",
                actor_id=uuid.UUID(int=0),
                payload={
                    "manifest_id": manifest_id,
                    "action": action,
                    "details": details or {},
                    "resource_type": "manifest",
                    "resource_id": manifest_id,
                },
            )
        except Exception:
            pass

    def _transition_job(
        self,
        manifest_id: str,
        status: str,
        errors: Optional[list] = None,
    ):
        self._job_statuses[manifest_id] = {
            "manifest_id": manifest_id,
            "status": status,
            "errors": errors,
            "transitioned_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_job_status(self, manifest_id: str) -> Optional[dict]:
        return self._job_statuses.get(manifest_id)

    def register_worker(
        self,
        worker_id: str,
        handler: Callable[[dict], dict],
        queue_name: str = "default",
    ) -> dict:
        if queue_name not in self._queues:
            self._queues[queue_name] = RedisQueue(queue_name)

        worker = {
            "worker_id": worker_id,
            "queue_name": queue_name,
            "handler": handler,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "registered",
            "tasks_processed": 0,
        }
        self._workers[worker_id] = worker
        return {"worker_id": worker_id, "queue_name": queue_name, "status": "registered"}

    def _start_heartbeat(self, worker_id: str, job_id: str):
        if not self._lease_manager:
            return

        def heartbeat_loop():
            while self._running:
                try:
                    result = self._lease_manager.record_heartbeat(job_id, worker_id)
                    if not result:
                        break
                except Exception:
                    break
                time.sleep(self._heartbeat_interval)

        key = f"{worker_id}:{job_id}"
        t = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_threads[key] = t
        t.start()

    def _stop_heartbeat(self, worker_id: str, job_id: str):
        key = f"{worker_id}:{job_id}"
        self._heartbeat_threads.pop(key, None)

    def execute_task(self, worker_id: str, task: dict) -> dict:
        worker = self._workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        manifest = task.get("manifest")
        if manifest:
            validated = self.validate_manifest(manifest)
            self._transition_job(validated.manifest_id, "running")

        handler = worker["handler"]
        worker["status"] = "busy"
        manifest_id = manifest.get("manifest_id", "<unknown>") if manifest else "<unknown>"
        job_id = task.get("job_id", manifest_id)

        self._start_heartbeat(worker_id, job_id)

        try:
            result = handler(task)
            worker["tasks_processed"] += 1
            worker["status"] = "idle"
            if manifest:
                self._transition_job(manifest_id, "completed")
            return result
        except ManifestValidationError:
            worker["status"] = "idle"
            raise
        except Exception as exc:
            worker["status"] = "error"
            if manifest:
                self._transition_job(manifest_id, "failed", errors=[str(exc)])
                self._write_audit_record(
                    manifest_id=manifest_id,
                    action="execution_failed",
                    details={"error": str(exc)},
                )
            raise
        finally:
            self._stop_heartbeat(worker_id, job_id)

    def submit_task(self, queue_name: str, task: dict) -> bool:
        if queue_name not in self._queues:
            self._queues[queue_name] = RedisQueue(queue_name)
        return self._queues[queue_name].enqueue(task)

    def get_worker_status(self, worker_id: str) -> Optional[dict]:
        worker = self._workers.get(worker_id)
        if not worker:
            return None
        return {
            "worker_id": worker["worker_id"],
            "queue_name": worker["queue_name"],
            "status": worker["status"],
            "tasks_processed": worker["tasks_processed"],
            "registered_at": worker["registered_at"],
        }

    def list_workers(self) -> List[dict]:
        return [self.get_worker_status(wid) for wid in self._workers]

    def start(self, poll_interval: float = 1.0):
        self._running = True
        for worker_id, worker in self._workers.items():
            queue_name = worker["queue_name"]
            t = threading.Thread(
                target=self._worker_loop,
                args=(worker_id, queue_name, poll_interval),
                daemon=True,
            )
            self._threads[worker_id] = t
            t.start()

    def stop(self):
        self._running = False
        for t in self._threads.values():
            t.join(timeout=5)
        self._threads.clear()
        self._heartbeat_threads.clear()

    def _worker_loop(self, worker_id: str, queue_name: str, poll_interval: float):
        queue = self._queues.get(queue_name)
        if not queue:
            return
        while self._running:
            task = queue.dequeue()
            if task:
                try:
                    self.execute_task(worker_id, task)
                except ManifestValidationError:
                    pass
                except Exception:
                    pass
            else:
                time.sleep(poll_interval)
