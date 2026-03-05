import uuid
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any, List

from app.social_platform.infrastructure.redis_queue import RedisQueue


class WorkerRuntime:
    def __init__(self):
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, RedisQueue] = {}
        self._running = False
        self._threads: Dict[str, threading.Thread] = {}

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

    def execute_task(self, worker_id: str, task: dict) -> dict:
        worker = self._workers.get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        handler = worker["handler"]
        worker["status"] = "busy"
        try:
            result = handler(task)
            worker["tasks_processed"] += 1
            worker["status"] = "idle"
            return result
        except Exception as exc:
            worker["status"] = "error"
            raise

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

    def _worker_loop(self, worker_id: str, queue_name: str, poll_interval: float):
        queue = self._queues.get(queue_name)
        if not queue:
            return
        while self._running:
            task = queue.dequeue()
            if task:
                try:
                    self.execute_task(worker_id, task)
                except Exception:
                    pass
            else:
                time.sleep(poll_interval)
